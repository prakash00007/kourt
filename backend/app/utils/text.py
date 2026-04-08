import re
from typing import Iterable


def normalize_whitespace(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_legal_text(text: str) -> str:
    text = normalize_whitespace(text)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.fullmatch(r"\d+", stripped):
            continue
        if len(stripped) < 3:
            continue
        lines.append(stripped)
    return "\n".join(lines)


def chunk_text(text: str, chunk_size_words: int = 400, overlap_words: int = 60) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + chunk_size_words)
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(end - overlap_words, 0)
    return chunks


def truncate_text(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).strip() + " ..."


def join_context_blocks(blocks: Iterable[str]) -> str:
    return "\n\n".join(block for block in blocks if block.strip())
