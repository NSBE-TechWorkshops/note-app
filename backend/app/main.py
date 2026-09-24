import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.database import Base, engine
from app import models  # noqa: F401 - imports model metadata for create_all
from app.routes import auth, documents, questions


# function for returning the correct origin
def _cors_origins() -> list[str]:
    origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in origins.split(",") if origin.strip()]


app = FastAPI(title="Note Buddy API")


@app.on_event("startup")
def init_db() -> None:
    # ponytail: create tables on startup for dev; replace with Alembic before prod
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)


# security for server
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# routes
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(questions.router)
