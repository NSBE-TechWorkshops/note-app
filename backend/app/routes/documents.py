import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.document import Document
from app.models.user import User
from app.services import s3_service, sqs_service

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_MIME_TYPES = {"application/pdf", "text/plain"}


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    course_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    # might add in user validation function to check and return error if not authenticated user
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_MIME_TYPES)}",
        )

    data = await file.read()
    doc = Document(
        user_id=user.id,
        course_id=course_id,
        original_filename=file.filename or "unnamed",
        s3_key="",  # set after upload
        mime_type=file.content_type,
        status="processing",
    )
    db.add(doc)
    db.flush()  # get doc.id

    s3_key = s3_service.upload_file(
        user.id, doc.id, doc.original_filename, data, doc.mime_type
    )
    doc.s3_key = s3_key
    db.commit()
    db.refresh(doc)

    sqs_service.send_process_document_message(doc.id)

    return {"id": str(doc.id), "status": doc.status, "filename": doc.original_filename}


@router.get("")
def list_documents(
    course_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    # might add in user validation function to check and return error if not authenticated user
    query = db.query(Document).filter(Document.user_id == user.id)
    if course_id:
        query = query.filter(Document.course_id == course_id)
    docs = query.order_by(Document.created_at.desc()).all()
    return [
        {
            "id": str(d.id),
            "filename": d.original_filename,
            "status": d.status,
            "mime_type": d.mime_type,
            "course_id": str(d.course_id) if d.course_id else None,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]


@router.get("/{document_id}")
def get_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    # might add in user validation function to check and return error if not authenticated user
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": str(doc.id),
        "filename": doc.original_filename,
        "status": doc.status,
        "mime_type": doc.mime_type,
        "course_id": str(doc.course_id) if doc.course_id else None,
        "error_message": doc.error_message,
        "created_at": doc.created_at.isoformat(),
    }


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    # might add in user validation function to check and return error if not authenticated user
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    s3_service.delete_file(doc.s3_key)
    db.delete(doc)  # cascades to chunks
    db.commit()
