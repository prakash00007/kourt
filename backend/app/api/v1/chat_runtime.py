import hashlib
import re

from fastapi import APIRouter, Depends

from app.api.deps import get_container, get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, Citation, SourceChunk
from app.services.container import ServiceContainer
from app.utils.text import truncate_text

router = APIRouter()


SIGNAL_STOPWORDS = {
    "about",
    "also",
    "and",
    "case",
    "cases",
    "give",
    "help",
    "here",
    "into",
    "legal",
    "law",
    "laws",
    "me",
    "need",
    "please",
    "query",
    "research",
    "show",
    "tell",
    "this",
    "those",
    "that",
    "the",
    "these",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
}


def _extract_signal_terms(query: str) -> tuple[set[str], bool]:
    tokens = re.findall(r"[A-Za-z0-9]+", query.lower())
    terms: set[str] = set()
    has_strong_anchor = False
    for token in tokens:
        if token.isdigit():
            terms.add(token)
            has_strong_anchor = True
            continue
        if len(token) < 4 or token in SIGNAL_STOPWORDS:
            continue
        terms.add(token)

    for token in re.findall(r"[A-Za-z0-9]+", query):
        if token.isdigit():
            has_strong_anchor = True
        elif token.isupper() and len(token) >= 3:
            has_strong_anchor = True

    return terms, has_strong_anchor


def _matches_query_terms(query_terms: set[str], anchor_terms: set[str], item: dict) -> bool:
    metadata = item.get("metadata") or {}
    text_parts = [
        str(metadata.get("title", "")),
        str(metadata.get("citation", "")),
        str(metadata.get("court", "")),
        item.get("text", ""),
    ]
    haystack = " ".join(text_parts).lower()

    if anchor_terms and not all(anchor in haystack for anchor in anchor_terms):
        return False

    if query_terms:
        return any(term in haystack for term in query_terms)
    return True


def _query_is_covered(query_terms: set[str], anchor_terms: set[str], retrieved: list[dict]) -> bool:
    if not query_terms:
        return True

    for item in retrieved:
        if _matches_query_terms(query_terms, anchor_terms, item):
            return True
    return False


def _build_gap_response(
    query: str,
    retrieved: list[dict],
    disclaimer: str,
    query_terms: set[str],
    anchor_terms: set[str],
) -> ChatResponse:
    citations: list[Citation] = []
    sources: list[SourceChunk] = []

    filtered_items = [item for item in retrieved if _matches_query_terms(query_terms, anchor_terms, item)]

    for index, item in enumerate(filtered_items, start=1):
        metadata = item.get("metadata") or {}
        title = metadata.get("title", f"Document {index}")
        citation = metadata.get("citation")
        court = metadata.get("court")
        source_url = metadata.get("source_url")
        excerpt = truncate_text(item.get("text", ""), 140)

        citations.append(
            Citation(
                title=title,
                citation=citation,
                court=court,
                source_url=source_url,
                relevance_score=item.get("score"),
            )
        )
        sources.append(
            SourceChunk(
                title=title,
                excerpt=excerpt,
                citation=citation,
                source_url=source_url,
            )
        )

    answer_lines = [
        "Direct Answer:",
        f"I could not find authorities matching '{query}' in the current knowledge base.",
        "",
        "Relevant Case Laws:",
    ]

    if citations:
        answer_lines.extend(
            f"- {item.title} | {item.citation or 'Citation unavailable'} | {item.court or 'Court not provided'}"
            for item in citations[:5]
        )
    else:
        answer_lines.append("- No close matches are currently indexed.")

    answer_lines.extend(
        [
            "",
            "Explanation:",
            "The indexed corpus does not appear to cover this topic yet, so I am not going to invent case law from unrelated materials. Upload the relevant judgments or connect a newer corpus, then re-run ingestion.",
        ]
    )
    if sources:
        answer_lines.extend(["", "Key Excerpts:"])
        answer_lines.extend(f"{index}. {item.excerpt}" for index, item in enumerate(sources[:3], start=1))

    return ChatResponse(
        answer="\n".join(answer_lines),
        citations=citations,
        sources=sources,
        disclaimer=disclaimer,
    )


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    container: ServiceContainer = Depends(get_container),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    cache_key = hashlib.sha256(payload.query.strip().lower().encode("utf-8")).hexdigest()
    retrieved = container.vector_store.search(payload.query, limit=container.settings.max_context_documents)
    query_terms, has_strong_anchor = _extract_signal_terms(payload.query)
    anchor_terms = {
        token.lower()
        for token in re.findall(r"[A-Za-z0-9]+", payload.query)
        if (token.isupper() and len(token) >= 3) or token.isdigit()
    }
    top_score = max((item.get("score") or 0.0) for item in retrieved) if retrieved else 0.0
    query_is_covered = _query_is_covered(query_terms, anchor_terms, retrieved)
    if query_terms and ((has_strong_anchor and not query_is_covered) or (top_score < 0.4 and not query_is_covered)):
        response = _build_gap_response(
            payload.query,
            retrieved,
            container.settings.disclaimer_text,
            query_terms,
            anchor_terms,
        )
        await container.cache_service.set_json("research", cache_key, response.model_dump(mode="json"))
        return response

    return await container.research_service.answer(payload)
