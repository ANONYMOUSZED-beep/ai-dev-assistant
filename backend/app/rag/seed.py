"""Seed content for the default "Getting Started" knowledge base.

These are short, original help documents about using AI Developer Assistant. Seeding
them means a brand-new user's very first question returns a real, cited answer instead
of an empty knowledge base — demonstrating the citation-grounded experience out of the
box. Seeding is idempotent (see ``RagPipeline.seed_if_empty``).
"""

from __future__ import annotations

from app.schemas.rag import Document, SourceType

GETTING_STARTED_COLLECTION = "getting-started"

_DOCS: list[tuple[str, str]] = [
    (
        "Welcome to AI Developer Assistant",
        "AI Developer Assistant helps you get answers grounded in your own documents "
        "and code. Every answer cites the sources it used, so you can trust and verify "
        "it. There are five modes: Docs (ask about documents you upload), Repo (ask "
        "about a code project), Search (find code by describing it), Debug (explain and "
        "fix an error), and Pair (explain, improve, or test code). Switch modes using "
        "the icons on the left rail.",
    ),
    (
        "How to add your own documents",
        "Open the Documentation section in the left panel and click the plus (+) "
        "button. You can paste text, add a link to a web page or PDF, or upload a file "
        "(PDF, Word, Markdown, HTML, or plain text). Give the set of documents a name "
        "(a knowledge base), for example 'Company Handbook'. After it is added, choose "
        "that knowledge base and ask questions about it in Docs mode. Answers will cite "
        "the exact parts of your documents they came from.",
    ),
    (
        "How to ask about a code project",
        "Go to the Repositories section in the left panel and paste a GitHub project "
        "address (for example owner/name), then click Add. The app reads the project, "
        "which can take a minute for large ones. When its status shows Ready, switch to "
        "Repo mode and ask questions like 'Give me an overview of this project' or "
        "'Where does login happen?'. Answers link back to the specific files.",
    ),
    (
        "Understanding citations",
        "Answers include numbered markers like [1] and [2]. Each marker points to a "
        "source shown in the Citations panel on the right. Click a citation to open the "
        "exact document section or code file it came from. If the app has no relevant "
        "documents, it will tell you instead of guessing — that is by design, so you "
        "always get answers you can verify.",
    ),
    (
        "Saving and revisiting chats",
        "Your conversations are saved automatically and appear under History in the "
        "left panel, tagged by type (Docs, Repo, Debug, or Pair). Click any past chat "
        "to reopen it, use New to start a fresh one, and the trash icon to delete one. "
        "Your documents, code projects, and chats are private to your account.",
    ),
]


def getting_started_documents() -> list[Document]:
    """Build the seed Document objects for the Getting Started knowledge base."""
    docs: list[Document] = []
    for i, (title, body) in enumerate(_DOCS, start=1):
        docs.append(
            Document(
                content=f"# {title}\n\n{body}",
                source_type=SourceType.MARKDOWN,
                source_id=f"getting-started/{i:02d}-{title.lower().replace(' ', '-')}.md",
                title=title,
                uri=None,
            )
        )
    return docs
