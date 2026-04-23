from app.utils.text import chunk_text, clean_legal_text, truncate_text


def test_chunk_text_returns_overlapping_chunks():
    text = " ".join(f"word{i}" for i in range(1, 41))
    chunks = chunk_text(text, chunk_size_words=10, overlap_words=2)
    assert len(chunks) >= 4
    assert chunks[0].split()[-2:] == chunks[1].split()[:2]


def test_clean_legal_text_removes_short_noise_lines():
    raw = "1\n\nA\nThis is valid text.\n2\nOk line"
    cleaned = clean_legal_text(raw)
    assert "This is valid text." in cleaned
    assert "\n1\n" not in f"\n{cleaned}\n"


def test_truncate_text_adds_ellipsis():
    raw = "one two three four five six"
    assert truncate_text(raw, 3) == "one two three ..."
