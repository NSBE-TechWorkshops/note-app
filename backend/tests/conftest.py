"""Shared fixtures.

Unit tests need nothing external. Tests marked `integration` need Postgres with the pgvector
extension and are skipped when none is reachable (CI sets REQUIRE_DB=1 so they can't be skipped there).

Local database:
    docker run -d --name notebuddy-test-db -p 5433:5432 \
        -e POSTGRES_USER=notebuddy -e POSTGRES_PASSWORD=notebuddy -e POSTGRES_DB=notebuddy_test \
        pgvector/pgvector:pg16
    export TEST_DATABASE_URL=postgresql://notebuddy:notebuddy@localhost:5433/notebuddy_test
"""

import os
import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://notebuddy:notebuddy@localhost:5432/notebuddy_test"
)
# The tests create and drop every table, so never let them near a real database.
if not (make_url(TEST_DATABASE_URL).database or "").endswith("_test"):
    raise RuntimeError("TEST_DATABASE_URL must point at a database whose name ends in '_test'")

# Settings are read when app modules are first imported, so set the environment before importing anything from app.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["LLM_API_KEY"] = "test-key"
os.environ["SQS_QUEUE_URL"] = ""
os.environ["AWS_REGION"] = "us-east-1"
os.environ["COGNITO_USER_POOL_ID"] = "us-east-1_TESTPOOL"
os.environ["COGNITO_CLIENT_ID"] = "test-client"
os.environ["COGNITO_REGION"] = "us-east-1"

from app.core import database  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.middleware.auth import get_current_user  # noqa: E402
from app.models import Document, DocumentChunk, User  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

EMBEDDING_DIM = 1536


def one_hot(index: int, weight: float = 1.0) -> list[float]:
    """A 1536-dim vector that is `weight` at `index` and 0 elsewhere (easy to reason about in cosine search)."""
    vector = [0.0] * EMBEDDING_DIM
    vector[index] = weight
    return vector


# ---------- database (integration) ----------


@pytest.fixture(scope="session")
def engine():
    try:
        with database.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        if os.environ.get("REQUIRE_DB"):
            raise
        pytest.skip(f"Postgres not reachable ({exc.__class__.__name__}); see tests/conftest.py to start one")
    with database.engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(database.engine)
    Base.metadata.create_all(database.engine)
    yield database.engine
    Base.metadata.drop_all(database.engine)


@pytest.fixture
def db(engine):
    """A session wrapped in a transaction that is rolled back after each test.

    `commit()` inside app code only releases a savepoint, so tests never leak data into each other.
    """
    connection = engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    yield session
    session.close()
    outer.rollback()
    connection.close()


@pytest.fixture
def session_factory(db):
    """Stand-in for SessionLocal that hands out sessions inside the same rolled-back transaction."""
    connection = db.get_bind()
    return lambda: Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)


@pytest.fixture
def make_user(db):
    def _make(name: str = "student") -> User:
        user = User(cognito_sub=f"sub-{name}-{uuid.uuid4().hex[:8]}", email=f"{name}@example.com")
        db.add(user)
        db.commit()
        return user

    return _make


@pytest.fixture
def user(make_user):
    return make_user("me")


@pytest.fixture
def make_document(db):
    """make_document(owner, chunks=[(text, vector), ...], status="ready") -> Document"""

    def _make(owner: User, chunks=(), status: str = "ready", filename: str = "notes.txt") -> Document:
        doc = Document(
            user_id=owner.id,
            original_filename=filename,
            s3_key=f"uploads/{owner.id}/{uuid.uuid4()}/{filename}",
            mime_type="text/plain",
            status=status,
        )
        db.add(doc)
        db.flush()
        for i, (chunk_text, vector) in enumerate(chunks):
            db.add(DocumentChunk(document_id=doc.id, chunk_text=chunk_text, chunk_index=i, embedding=vector))
        db.commit()
        return doc

    return _make


@pytest.fixture
def client(db, user):
    """API client that is logged in as `user` and uses the transactional test database."""
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------- no database needed ----------


@pytest.fixture
def unit_client():
    """API client with a fake logged-in user and a mock DB session, for routes that fail before touching the DB."""
    stub_user = User(id=uuid.uuid4(), cognito_sub="stub", email="stub@example.com")
    app.dependency_overrides[get_db] = lambda: MagicMock()
    app.dependency_overrides[get_current_user] = lambda: stub_user
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def anon_client():
    """API client with no auth override, so the real JWT checks run."""
    app.dependency_overrides.clear()
    return TestClient(app)
