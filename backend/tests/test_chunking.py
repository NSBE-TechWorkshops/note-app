from types import SimpleNamespace

from app.services import document_processor as dp


def make_words(n: int) -> list[str]:
    return [f"word{i}" for i in range(n)]


def test_short_text_stays_in_one_chunk():
    assert dp._splitter.split_text("A short note about mitochondria.") == ["A short note about mitochondria."]


def test_empty_text_produces_no_chunks():
    assert dp._splitter.split_text("") == []


def test_chunks_respect_the_1000_character_limit():
    chunks = dp._splitter.split_text(" ".join(make_words(2000)))

    assert len(chunks) > 1
    assert all(len(chunk) <= 1000 for chunk in chunks)


def test_neighbouring_chunks_overlap():
    chunks = dp._splitter.split_text(" ".join(make_words(2000)))

    for current, following in zip(chunks, chunks[1:]):
        assert current.split()[-1] in following.split(), "end of a chunk should reappear at the start of the next"


def test_no_text_is_lost_between_chunks():
    words = make_words(2000)
    chunks = dp._splitter.split_text(" ".join(words))

    covered = {word for chunk in chunks for word in chunk.split()}
    assert covered == set(words)


def test_extract_text_decodes_plain_text():
    assert dp._extract_text("hello notes".encode(), "text/plain") == "hello notes"


def test_extract_text_replaces_invalid_bytes_instead_of_crashing():
    assert "ok" in dp._extract_text(b"ok \xff\xfe", "text/plain")


def test_extract_text_joins_pdf_pages_and_tolerates_empty_pages(monkeypatch):
    pages = [SimpleNamespace(extract_text=lambda: "page one"), SimpleNamespace(extract_text=lambda: None)]
    monkeypatch.setattr(dp, "PdfReader", lambda _: SimpleNamespace(pages=pages))

    assert dp._extract_text(b"%PDF-fake", "application/pdf") == "page one\n"
