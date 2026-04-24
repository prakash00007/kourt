from typing import Any, TypedDict


class ResearchGraphState(TypedDict, total=False):
    query: str
    plan: dict[str, Any]
    retrieval: dict[str, Any]
    answer: str
    verification_note: str
    trace: list[dict[str, Any]]
