import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.question import Question
from app.models.question_source import QuestionSource
from app.models.user import User
from app.services import embedding_service, llm_service

router = APIRouter(prefix="/questions", tags=["questions"])

TOP_K = 5


class AskRequest(BaseModel):
    question: str
    course_id: uuid.UUID | None = None


@router.post("/ask")
def ask(
    body: AskRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    # Build base query for user's ready document chunks
    chunk_query = (
        db.query(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .filter(Document.user_id == user.id, Document.status == "ready")
    )
    if body.course_id:
        chunk_query = chunk_query.filter(Document.course_id == body.course_id)

    # Check user has any chunks
    if chunk_query.count() == 0:
        raise HTTPException(status_code=400, detail="No ready documents to search. Upload and wait for processing.")

    # Embed question and retrieve nearest chunks via pgvector
    question_vector = embedding_service.create_embedding(body.question)
    nearest = (
        chunk_query
        .order_by(DocumentChunk.embedding.cosine_distance(question_vector))
        .limit(TOP_K)
        .all()
    )

    if not nearest:
        raise HTTPException(status_code=400, detail="No relevant chunks found.")

    # Generate answer
    context_texts = [c.chunk_text for c in nearest]
    answer_text, model_used = llm_service.generate_answer(body.question, context_texts)

    # Persist question
    question = Question(
        user_id=user.id,
        course_id=body.course_id,
        question_text=body.question,
        answer_text=answer_text,
        model_used=model_used,
    )
    db.add(question)
    db.flush()

    # Persist sources with relevance scores
    for i, chunk in enumerate(nearest):
        db.add(QuestionSource(
            question_id=question.id,
            document_chunk_id=chunk.id,
            relevance_score=1.0 / (i + 1),  # ponytail: rank-based score, replace with actual distance if needed
        ))

    db.commit()
    db.refresh(question)

    return {
        "id": str(question.id),
        "question": question.question_text,
        "answer": question.answer_text,
        "model": question.model_used,
        "sources": [
            {"chunk_id": str(c.id), "text_preview": c.chunk_text[:200], "document_id": str(c.document_id)}
            for c in nearest
        ],
    }


@router.get("")
def list_questions(
    course_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    query = db.query(Question).filter(Question.user_id == user.id)
    if course_id:
        query = query.filter(Question.course_id == course_id)
    questions = query.order_by(Question.created_at.desc()).all()
    return [
        {
            "id": str(q.id),
            "question": q.question_text,
            "answer_preview": q.answer_text[:200],
            "model": q.model_used,
            "created_at": q.created_at.isoformat(),
        }
        for q in questions
    ]


@router.get("/{question_id}")
def get_question(
    question_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    question = db.query(Question).filter(Question.id == question_id, Question.user_id == user.id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    sources = db.query(QuestionSource).filter(QuestionSource.question_id == question.id).all()
    chunk_ids = [s.document_chunk_id for s in sources]
    chunks = db.query(DocumentChunk).filter(DocumentChunk.id.in_(chunk_ids)).all() if chunk_ids else []
    chunk_map = {c.id: c for c in chunks}

    return {
        "id": str(question.id),
        "question": question.question_text,
        "answer": question.answer_text,
        "model": question.model_used,
        "created_at": question.created_at.isoformat(),
        "sources": [
            {
                "chunk_id": str(s.document_chunk_id),
                "relevance_score": s.relevance_score,
                "text": chunk_map[s.document_chunk_id].chunk_text if s.document_chunk_id in chunk_map else None,
                "document_id": str(chunk_map[s.document_chunk_id].document_id) if s.document_chunk_id in chunk_map else None,
            }
            for s in sources
        ],
    }
