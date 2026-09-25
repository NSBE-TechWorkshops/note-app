"""Retrieval against a real pgvector index: the point is that the *right chunks* come back, in order."""

import pytest

from app.models import Question, QuestionSource
from app.routes import questions as questions_route
from tests.conftest import one_hot


@pytest.fixture
def fake_llm(monkeypatch):
    """Replaces OpenAI. Records the chunks the route sent as context."""
    calls = {}

    def generate_answer(question, context_chunks):
        calls["question"], calls["context"] = question, list(context_chunks)
        return "fake answer", "fake-model"

    monkeypatch.setattr(questions_route.llm_service, "generate_answer", generate_answer)
    return calls


def question_embeds_as(monkeypatch, vector):
    monkeypatch.setattr(questions_route.embedding_service, "create_embedding", lambda _text: vector)


@pytest.mark.integration
def test_ask_without_ready_documents_is_a_400(client, fake_llm):
    response = client.post("/questions/ask", json={"question": "What is ATP?"})

    assert response.status_code == 400
    assert "No ready documents" in response.json()["detail"]


@pytest.mark.integration
def test_closest_chunks_come_back_first(client, db, user, make_document, fake_llm, monkeypatch):
    make_document(user, chunks=[("about ribosomes", one_hot(0)), ("about mitochondria", one_hot(1)),
                                ("about the nucleus", one_hot(2))])
    # Mostly points at "mitochondria", a little at "ribosomes", not at all at "nucleus"
    mixed = [a + b for a, b in zip(one_hot(1, 0.9), one_hot(0, 0.1))]
    question_embeds_as(monkeypatch, mixed)

    response = client.post("/questions/ask", json={"question": "What do mitochondria do?"})

    assert response.status_code == 200
    assert fake_llm["context"] == ["about mitochondria", "about ribosomes", "about the nucleus"]
    body = response.json()
    assert body["answer"] == "fake answer"
    assert body["model"] == "fake-model"
    assert body["sources"][0]["text_preview"] == "about mitochondria"
    assert db.query(Question).count() == 1
    assert db.query(QuestionSource).count() == 3


@pytest.mark.integration
def test_only_the_top_five_chunks_are_used(client, user, make_document, fake_llm, monkeypatch):
    make_document(user, chunks=[(f"chunk {i}", one_hot(i)) for i in range(8)])
    question_embeds_as(monkeypatch, one_hot(0))

    client.post("/questions/ask", json={"question": "anything"})

    assert len(fake_llm["context"]) == questions_route.TOP_K == 5
    assert fake_llm["context"][0] == "chunk 0"


@pytest.mark.integration
def test_other_students_notes_are_never_retrieved(client, user, make_user, make_document, fake_llm, monkeypatch):
    make_document(user, chunks=[("my notes", one_hot(5))])
    # A perfect match for the question, but it belongs to someone else
    make_document(make_user("someone-else"), chunks=[("their private notes", one_hot(0))])
    question_embeds_as(monkeypatch, one_hot(0))

    client.post("/questions/ask", json={"question": "anything"})

    assert fake_llm["context"] == ["my notes"]


@pytest.mark.integration
def test_documents_still_processing_are_ignored(client, user, make_document, fake_llm, monkeypatch):
    make_document(user, chunks=[("half-processed", one_hot(0))], status="processing")
    make_document(user, chunks=[("finished", one_hot(3))], status="ready")
    question_embeds_as(monkeypatch, one_hot(0))

    client.post("/questions/ask", json={"question": "anything"})

    assert fake_llm["context"] == ["finished"]
