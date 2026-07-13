"""Context-aware prompt templates.

Each builder returns a list of :class:`LLMMessage` ready for any provider. Retrieved
context is injected as numbered blocks so the model can cite sources as ``[n]`` and the
service layer can map those markers back to :class:`Citation` objects.
"""

from __future__ import annotations

from app.schemas.chat import PairAction
from app.schemas.llm import LLMMessage, Role
from app.schemas.rag import RetrievedChunk

_CITATION_RULES = (
    "Ground every claim in the provided context. Cite sources inline using bracketed "
    "numbers like [1], [2] that refer to the numbered context blocks. If the context is "
    "insufficient, say so explicitly instead of inventing an answer. Provide working, "
    "production-ready code examples where helpful, and never use placeholder comments."
)


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Render retrieved chunks as numbered, attributable context blocks."""
    if not chunks:
        return "(no context retrieved)"
    blocks: list[str] = []
    for i, rc in enumerate(chunks, start=1):
        c = rc.chunk
        location = c.uri or c.source_id
        if c.start_line is not None:
            location = f"{location}:{c.start_line}-{c.end_line or c.start_line}"
        header = f"[{i}] {c.title or c.source_id} ({location})"
        blocks.append(f"{header}\n{c.content.strip()}")
    return "\n\n".join(blocks)


_REPO_REDIRECT_RULE = (
    "This is the Documentation chat, grounded in the selected documentation library. "
    "If the user is instead asking about their own uploaded/indexed repository or a "
    "specific personal codebase (for example: 'my repo', 'this project', a particular "
    "file or function in their code, or why their own code behaves a certain way), do "
    "not guess from the documentation. Instead, politely and warmly let them know this "
    "is the Documentation chat and gently suggest they switch to the 'Repo' chat tab "
    "and select their repository to get accurate, code-specific answers. Keep that "
    "redirect brief and friendly, and still offer to help with any general "
    "documentation question."
)


def build_doc_qa_messages(question: str, chunks: list[RetrievedChunk]) -> list[LLMMessage]:
    system = (
        "You are an expert software engineering assistant answering questions using "
        "official documentation. " + _CITATION_RULES + " " + _REPO_REDIRECT_RULE
    )
    user = (
        f"Context:\n{format_context(chunks)}\n\n"
        f"Question: {question}\n\n"
        "Answer with a clear explanation, best practices, and a runnable code example "
        "when relevant. End with a 'Sources' list of the citation numbers you used."
    )
    return [LLMMessage(role=Role.SYSTEM, content=system), LLMMessage(role=Role.USER, content=user)]


def build_repo_qa_messages(question: str, chunks: list[RetrievedChunk]) -> list[LLMMessage]:
    system = (
        "You are a senior engineer who has just read this repository. Explain "
        "architecture, files, classes, and functions precisely, and point to where logic "
        "lives. " + _CITATION_RULES
    )
    user = (
        f"Repository context:\n{format_context(chunks)}\n\n"
        f"Question: {question}\n\n"
        "Reference specific files and line ranges from the context using [n] markers."
    )
    return [LLMMessage(role=Role.SYSTEM, content=system), LLMMessage(role=Role.USER, content=user)]


def build_repo_overview_messages(chunks: list[RetrievedChunk]) -> list[LLMMessage]:
    system = (
        "You are a senior engineer writing a concise onboarding overview of a repository "
        "from the provided code context. Produce a one-page markdown tour with these "
        "sections: 'What this project is', 'Key modules & entry points', 'How to run it' "
        "(best-effort, only if inferable from the context), and 'Where to look next'. "
        "Cite files with [n] using the numbered context. Keep it grounded: if something "
        "is not evident from the context, say so briefly rather than inventing it. "
        + _CITATION_RULES
    )
    user = f"Repository context:\n{format_context(chunks)}"
    return [LLMMessage(role=Role.SYSTEM, content=system), LLMMessage(role=Role.USER, content=user)]


def build_debug_messages(
    error: str,
    chunks: list[RetrievedChunk],
    language: str | None = None,
    code_context: str | None = None,
) -> list[LLMMessage]:
    system = (
        "You are an expert debugger. Analyse the stack trace, identify the root cause, "
        "and provide corrected, production-ready code. " + _CITATION_RULES
    )
    parts = [f"Error / stack trace:\n{error}"]
    if language:
        parts.append(f"Language: {language}")
    if code_context:
        parts.append(f"Relevant code:\n{code_context}")
    parts.append(f"Reference context:\n{format_context(chunks)}")
    parts.append(
        "Respond with: 1) Root cause, 2) Fix explanation, 3) Corrected code, "
        "4) How to prevent it. Cite context with [n] where applicable."
    )
    user = "\n\n".join(parts)
    return [LLMMessage(role=Role.SYSTEM, content=system), LLMMessage(role=Role.USER, content=user)]


_PAIR_INSTRUCTIONS: dict[PairAction, str] = {
    PairAction.EXPLAIN: (
        "Explain what this code does, step by step, including its intent and edge cases."
    ),
    PairAction.REFACTOR: (
        "Refactor this code for readability and maintainability without changing "
        "behaviour. Return the full refactored code."
    ),
    PairAction.TEST: (
        "Generate a thorough unit test suite for this code using the language's "
        "idiomatic test framework."
    ),
    PairAction.DOCUMENT: (
        "Add complete docstrings/comments and produce concise reference documentation "
        "for this code."
    ),
    PairAction.OPTIMIZE: (
        "Identify performance bottlenecks and return an optimised version with an "
        "explanation of the gains."
    ),
    PairAction.SECURITY: (
        "Perform a security review: list vulnerabilities by severity and provide "
        "hardened code."
    ),
}


def build_followups_messages(question: str, answer_text: str) -> list[LLMMessage]:
    """Prompt the model to suggest short follow-up questions the user might ask next."""
    system = (
        "You suggest natural follow-up questions a user might ask next in a technical "
        "chat. Suggest exactly 3 short questions, each on its own line, at most about 8 "
        "words each. Do not number them, do not use bullets or quotes, and output ONLY "
        "the questions with nothing else."
    )
    user = (
        f"Original question: {question}\n\n"
        f"Answer given:\n{answer_text}\n\n"
        "Suggest 3 follow-up questions."
    )
    return [LLMMessage(role=Role.SYSTEM, content=system), LLMMessage(role=Role.USER, content=user)]


def build_pair_messages(
    action: PairAction,
    code: str,
    chunks: list[RetrievedChunk],
    language: str | None = None,
    instructions: str | None = None,
) -> list[LLMMessage]:
    system = (
        "You are an AI pair programmer producing production-ready output. Use type hints "
        "and idiomatic style; never emit placeholder or TODO code. " + _CITATION_RULES
    )
    task = _PAIR_INSTRUCTIONS[action]
    parts = [f"Task: {task}"]
    if language:
        parts.append(f"Language: {language}")
    if instructions:
        parts.append(f"Additional instructions: {instructions}")
    parts.append(f"Code:\n```\n{code}\n```")
    if chunks:
        parts.append(f"Reference context:\n{format_context(chunks)}")
    user = "\n\n".join(parts)
    return [LLMMessage(role=Role.SYSTEM, content=system), LLMMessage(role=Role.USER, content=user)]
