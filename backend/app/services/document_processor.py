"""Document processing pipeline: download → parse → chunk → embed → store."""

import io
import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services import embedding_service, s3_service

_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)


def _extract_text(data: bytes, mime_type: str) -> str:
    if mime_type == "application/pdf":
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    # Default: treat as plain text
    return data.decode("utf-8", errors="replace")


def process_document(document_id: uuid.UUID) -> None:
    """Full processing pipeline. Safe to call from Lambda or any worker."""
    db: Session = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc is None:
            return

        # Download
        data = s3_service.download_file(doc.s3_key)

        # Parse
        text = _extract_text(data, doc.mime_type)
        if not text.strip():
            doc.status = "failed"
            doc.error_message = "No text could be extracted from the document."
            db.commit()
            return

        # Chunk
        chunks = _splitter.split_text(text)

        # Embed
        vectors = embedding_service.create_embeddings(chunks)

        # Store
        for i, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
            db.add(DocumentChunk(
                document_id=doc.id,
                chunk_text=chunk_text,
                chunk_index=i,
                embedding=vector,
                token_count=len(chunk_text.split()),  # ponytail: naive word count, use tiktoken if accuracy matters
            ))

        doc.status = "ready"
        db.commit()

    except Exception as exc:
        db.rollback()
        # Try to mark as failed
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = "failed"
                doc.error_message = str(exc)[:2000]
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()
