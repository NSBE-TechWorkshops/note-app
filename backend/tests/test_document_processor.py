"""The ingestion pipeline (parse -> chunk -> embed -> store) with S3 and OpenAI faked out."""

import uuid

import pytest

from app.models import DocumentChunk
from app.services import document_processor as dp
from tests.conftest import EMBEDDING_DIM, one_hot

LONG_NOTE = " ".join(f"sentence{i} about cells." for i in range(300))  # a few thousand characters


@pytest.fixture
def pipeline(db, session_factory, monkeypatch):
    """Points the pipeline at the test DB and records what it sent to the fake embedding service."""
    calls = {"embedded": []}

    def fake_embeddings(chunks):
        calls["embedded"].append(list(chunks))
        return [one_hot(i % EMBEDDING_DIM) for i in range(len(chunks))]

    monkeypatch.setattr(dp, "SessionLocal", session_factory)
    monkeypatch.setattr(dp.embedding_service, "create_embeddings", fake_embeddings)
    return calls


def stored_chunks(db, doc):
    db.expire_all()
    return db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index).all()


@pytest.mark.integration
def test_document_becomes_ready_with_one_row_per_chunk(db, user, make_document, pipeline, monkeypatch):
    doc = make_document(user, status="processing")
    monkeypatch.setattr(dp.s3_service, "download_file", lambda key: LONG_NOTE.encode())

    dp.process_document(doc.id)

    db.refresh(doc)
    chunks = stored_chunks(db, doc)
    assert doc.status == "ready"
    assert len(chunks) == len(dp._splitter.split_text(LONG_NOTE)) > 1
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert all(len(c.chunk_text) <= 1000 for c in chunks)
    assert all(len(c.embedding) == EMBEDDING_DIM for c in chunks)
    assert pipeline["embedded"] == [[c.chunk_text for c in chunks]], "every chunk is embedded exactly once"


@pytest.mark.integration
def test_document_with_no_text_is_marked_failed(db, user, make_document, pipeline, monkeypatch):
    doc = make_document(user, status="processing")
    monkeypatch.setattr(dp.s3_service, "download_file", lambda key: b"   \n  ")

    dp.process_document(doc.id)

    db.refresh(doc)
    assert doc.status == "failed"
    assert "No text" in doc.error_message
    assert pipeline["embedded"] == []
    assert stored_chunks(db, doc) == []


@pytest.mark.integration
def test_embedding_failure_marks_document_failed_and_raises(db, user, make_document, pipeline, monkeypatch):
    doc = make_document(user, status="processing")
    monkeypatch.setattr(dp.s3_service, "download_file", lambda key: LONG_NOTE.encode())

    def explode(chunks):
        raise RuntimeError("OpenAI is down")

    monkeypatch.setattr(dp.embedding_service, "create_embeddings", explode)

    with pytest.raises(RuntimeError, match="OpenAI is down"):
        dp.process_document(doc.id)

    db.refresh(doc)
    assert doc.status == "failed"
    assert "OpenAI is down" in doc.error_message
    assert stored_chunks(db, doc) == []


@pytest.mark.integration
def test_unknown_document_id_is_ignored(pipeline):
    dp.process_document(uuid.uuid4())  # must not raise

    assert pipeline["embedded"] == []
