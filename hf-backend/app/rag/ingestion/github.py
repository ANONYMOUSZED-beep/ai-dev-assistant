"""GitHub repository ingestion.

When a token is available the GitHub API (PyGithub) is used to walk the repository
tree; otherwise the public tarball is streamed via ``httpx``. Code files are tagged
``SourceType.CODE``; binaries and oversized files are skipped.
"""

from __future__ import annotations

import io
import os
import tarfile
from urllib.parse import urlparse

from tenacity import retry, stop_after_attempt, wait_exponential

from app.rag.ingestion.loaders import _CODE_EXTENSIONS, _PROSE_EXTENSIONS
from app.schemas.rag import Document, SourceType

# Text extensions worth indexing in addition to code (docs inside the repo).
_TEXT_EXTENSIONS: set[str] = _CODE_EXTENSIONS | {
    ".md", ".markdown", ".mdx", ".txt", ".rst", ".cfg", ".ini", ".toml",
}
_DOC_EXTENSIONS = {".md", ".markdown", ".mdx", ".rst", ".txt"}

_MAX_FILE_BYTES = 512 * 1024  # Skip files larger than 512 KiB.
_HTTP_TIMEOUT = 60.0
_USER_AGENT = "ai-dev-assistant/1.0 (+github)"


def _parse_owner_repo(url: str) -> tuple[str, str]:
    """Extract ``(owner, repo)`` from a GitHub URL or ``owner/repo`` string."""
    candidate = url.strip()
    if candidate.startswith("http://") or candidate.startswith("https://"):
        path = urlparse(candidate).path
    else:
        path = candidate
    parts = [p for p in path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from {url!r}")
    owner, repo = parts[0], parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo


def _source_type_for(path: str) -> SourceType | None:
    """Return the indexing source type for a repo path, or ``None`` to skip."""
    ext = os.path.splitext(path)[1].lower()
    if ext in _CODE_EXTENSIONS:
        return SourceType.CODE
    if ext in _DOC_EXTENSIONS or ext in _PROSE_EXTENSIONS:
        return SourceType.MARKDOWN if ext in {".md", ".markdown", ".mdx"} else SourceType.TXT
    return None


def _make_document(
    owner: str, repo: str, path: str, content: str, url: str | None
) -> Document:
    source_type = _source_type_for(path) or SourceType.CODE
    ext = os.path.splitext(path)[1].lower()
    metadata: dict[str, object] = {"repo": f"{owner}/{repo}", "path": path}
    if source_type == SourceType.CODE and ext:
        metadata["language"] = ext.lstrip(".")
    return Document(
        content=content,
        source_type=source_type,
        source_id=f"{owner}/{repo}:{path}",
        title=path,
        uri=url,
        metadata=metadata,
    )


def load_github_repo(
    url: str, branch: str | None = None, github_token: str | None = None
) -> list[Document]:
    """Load indexable files from a GitHub repository as :class:`Document` objects."""
    owner, repo = _parse_owner_repo(url)
    if github_token:
        return _load_via_api(owner, repo, branch, github_token)
    return _load_via_tarball(owner, repo, branch)


# ── GitHub API path (PyGithub) ───────────────────────────────────
def _load_via_api(
    owner: str, repo: str, branch: str | None, token: str
) -> list[Document]:
    from github import Github

    client = Github(token)
    repository = client.get_repo(f"{owner}/{repo}")
    ref = branch or repository.default_branch
    tree = repository.get_git_tree(ref, recursive=True)

    documents: list[Document] = []
    for element in tree.tree:
        if element.type != "blob" or element.path is None:
            continue
        if _source_type_for(element.path) is None:
            continue
        if element.size is not None and element.size > _MAX_FILE_BYTES:
            continue
        text = _read_blob(repository, element.path, ref)
        if text is None:
            continue
        html_url = f"https://github.com/{owner}/{repo}/blob/{ref}/{element.path}"
        documents.append(_make_document(owner, repo, element.path, text, html_url))
    return documents


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=8.0),
    reraise=True,
)
def _read_blob(repository: object, path: str, ref: str) -> str | None:
    contents = repository.get_contents(path, ref=ref)  # type: ignore[attr-defined]
    if isinstance(contents, list):
        return None
    raw = contents.decoded_content
    if raw is None:
        return None
    return raw.decode("utf-8", errors="replace")


# ── Tarball path (httpx, no token) ───────────────────────────────
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=8.0),
    reraise=True,
)
def _fetch_tarball(owner: str, repo: str, ref: str) -> bytes:
    import httpx

    url = f"https://codeload.github.com/{owner}/{repo}/tar.gz/{ref}"
    with httpx.Client(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
        response = client.get(url, headers={"User-Agent": _USER_AGENT})
        response.raise_for_status()
        return response.content


def _load_via_tarball(owner: str, repo: str, branch: str | None) -> list[Document]:
    refs = [branch] if branch else ["main", "master", "HEAD"]
    last_error: Exception | None = None
    data: bytes | None = None
    for ref in refs:
        try:
            data = _fetch_tarball(owner, repo, ref)
            break
        except Exception as exc:  # noqa: BLE001 - try the next candidate ref
            last_error = exc
    if data is None:
        raise RuntimeError(
            f"Failed to fetch tarball for {owner}/{repo}: {last_error}"
        )

    documents: list[Document] = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile() or member.size > _MAX_FILE_BYTES:
                continue
            rel_path = _strip_root(member.name)
            if not rel_path or _source_type_for(rel_path) is None:
                continue
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            raw = extracted.read()
            if _looks_binary(raw):
                continue
            text = raw.decode("utf-8", errors="replace")
            html_url = f"https://github.com/{owner}/{repo}/blob/{branch or 'HEAD'}/{rel_path}"
            documents.append(_make_document(owner, repo, rel_path, text, html_url))
    return documents


def _strip_root(name: str) -> str:
    """Drop the leading ``repo-ref/`` directory that GitHub tarballs prepend."""
    parts = name.split("/", 1)
    return parts[1] if len(parts) == 2 else ""


def _looks_binary(raw: bytes) -> bool:
    return b"\x00" in raw[:4096]
