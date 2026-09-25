import uuid

import pytest

from app.models import Document, DocumentChunk
from app.routes import documents as documents_route
from tests.conftest import one_hot


def test_upload_rejects_unsupported_file_type(unit_client):
    response = unit_client.post("/documents/upload", files={"file": ("photo.png", b"not a note", "image/png")})

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


@pytest.mark.integration
def test_upload_stores_file_creates_record_and_queues_a_job(client, db, user, monkeypatch):
    uploaded, queued = [], []

    def fake_upload(user_id, document_id, filename, data, content_type):
        uploaded.append((user_id, document_id, filename, data, content_type))
        return f"uploads/{user_id}/{document_id}/{filename}"

    monkeypatch.setattr(documents_route.s3_service, "upload_file", fake_upload)
    monkeypatch.setattr(documents_route.sqs_service, "send_process_document_message", queued.append)

    response = client.post("/documents/upload", files={"file": ("bio.txt", b"cells are small", "text/plain")})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "processing"
    assert body["filename"] == "bio.txt"

    doc = db.get(Document, uuid.UUID(body["id"]))
    assert doc.user_id == user.id
    assert doc.s3_key.startswith(f"uploads/{user.id}/")
    assert uploaded[0][3] == b"cells are small"
    assert queued == [doc.id]


@pytest.mark.integration
def test_list_documents_only_returns_my_documents(client, user, make_user, make_document):
    mine = make_document(user, filename="mine.txt")
    make_document(make_user("someone-else"), filename="theirs.txt")

    response = client.get("/documents")

    assert response.status_code == 200
    assert [d["id"] for d in response.json()] == [str(mine.id)]


@pytest.mark.integration
def test_cannot_read_someone_elses_document(client, make_user, make_document):
    theirs = make_document(make_user("someone-else"))

    assert client.get(f"/documents/{theirs.id}").status_code == 404


@pytest.mark.integration
def test_get_document_shows_processing_status(client, user, make_document):
    doc = make_document(user, status="processing")

    response = client.get(f"/documents/{doc.id}")

    assert response.status_code == 200
    assert response.json()["status"] == "processing"


@pytest.mark.integration
def test_delete_removes_document_its_chunks_and_the_s3_file(client, db, user, make_document, monkeypatch):
    deleted_keys = []
    monkeypatch.setattr(documents_route.s3_service, "delete_file", deleted_keys.append)
    doc = make_document(user, chunks=[("chunk one", one_hot(0)), ("chunk two", one_hot(1))])

    response = client.delete(f"/documents/{doc.id}")

    assert response.status_code == 204
    assert deleted_keys == [doc.s3_key]
    assert db.query(Document).count() == 0
    assert db.query(DocumentChunk).count() == 0


@pytest.mark.integration
def test_cannot_delete_someone_elses_document(client, make_user, make_document, monkeypatch):
    monkeypatch.setattr(documents_route.s3_service, "delete_file", lambda key: pytest.fail("must not delete"))
    theirs = make_document(make_user("someone-else"))

    assert client.delete(f"/documents/{theirs.id}").status_code == 404
