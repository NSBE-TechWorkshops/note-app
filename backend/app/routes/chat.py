import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.services import embedding_service, llm_service

router = APIRouter(prefix="/chat", tags=["chat"])

TOP_K = 5


class CreateSessionRequest(BaseModel):
    title: str | None = None
    course_id: uuid.UUID | None = None


class SendMessageRequest(BaseModel):
    content: str
    session_id: uuid.UUID | None = None
    document_ids: list[uuid.UUID] | None = None


def _session_payload(session: ChatSession) -> dict:
    return {
        "id": str(session.id),
        "title": session.title,
        "course_id": str(session.course_id) if session.course_id else None,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


def _message_payload(message: ChatMessage) -> dict:
    return {
        "id": str(message.id),
        "role": message.role,
        "content": message.content,
        "model": message.model_used,
        "created_at": message.created_at.isoformat(),
    }


def _answer_prompt(prompt: str, course_id: uuid.UUID | None, document_ids: list[uuid.UUID] | None, user: User, db: Session) -> tuple[str, str, list[DocumentChunk]]:
    chunk_query = (
        db.query(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .filter(Document.user_id == user.id, Document.status == "ready")
    )
    if course_id:
        chunk_query = chunk_query.filter(Document.course_id == course_id)
    if document_ids:
        chunk_query = chunk_query.filter(Document.id.in_(document_ids))

    if chunk_query.count() == 0:
        raise HTTPException(status_code=400, detail="No ready documents to search. Upload/select documents and wait for processing.")

    question_vector = embedding_service.create_embedding(prompt)
    nearest = (
        chunk_query
        .order_by(DocumentChunk.embedding.cosine_distance(question_vector))
        .limit(TOP_K)
        .all()
    )
    if not nearest:
        raise HTTPException(status_code=400, detail="No relevant chunks found.")

    answer_text, model_used = llm_service.generate_answer(prompt, [chunk.chunk_text for chunk in nearest])
    return answer_text, model_used, nearest


def _persist_turn(session: ChatSession, prompt: str, answer_text: str, model_used: str, db: Session) -> list[ChatMessage]:
    user_message = ChatMessage(session_id=session.id, role="user", content=prompt)
    assistant_message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer_text,
        model_used=model_used,
    )
    session.updated_at = datetime.now(timezone.utc)
    db.add(user_message)
    db.add(assistant_message)
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    db.refresh(session)
    return [user_message, assistant_message]


def _send_message_payload(session: ChatSession, messages: list[ChatMessage], sources: list[DocumentChunk]) -> dict:
    return {
        "session": _session_payload(session),
        "messages": [_message_payload(message) for message in messages],
        "sources": [
            {"chunk_id": str(chunk.id), "text_preview": chunk.chunk_text[:200], "document_id": str(chunk.document_id)}
            for chunk in sources
        ],
    }


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(
    body: CreateSessionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    title = (body.title or "New chat").strip()[:255] or "New chat"
    session = ChatSession(user_id=user.id, course_id=body.course_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_payload(session)


@router.get("/sessions")
def list_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return [_session_payload(session) for session in sessions]


@router.get("/sessions/{session_id}")
def get_session(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return {**_session_payload(session), "messages": [_message_payload(message) for message in messages]}


@router.post("/sessions/{session_id}/messages")
def send_message(
    session_id: uuid.UUID,
    body: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    prompt = body.content.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Message content is required")

    answer_text, model_used, sources = _answer_prompt(prompt, session.course_id, body.document_ids, user, db)
    messages = _persist_turn(session, prompt, answer_text, model_used, db)
    return _send_message_payload(session, messages, sources)


@router.post("/messages", status_code=status.HTTP_201_CREATED)
def start_session_with_message(
    body: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    prompt = body.content.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Message content is required")

    if body.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == body.session_id, ChatSession.user_id == user.id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        session = ChatSession(user_id=user.id, title=prompt[:80])
        db.add(session)
        db.flush()

    answer_text, model_used, sources = _answer_prompt(prompt, session.course_id, body.document_ids, user, db)
    messages = _persist_turn(session, prompt, answer_text, model_used, db)
    return _send_message_payload(session, messages, sources)
