# Note Buddy — Backend

FastAPI backend for the Note Buddy student notes RAG application.

## Architecture

```text
Client (React + Cognito JWT)
  │
  ▼
FastAPI (ECS/Fargate)
  ├── /health              public health check
  ├── /me                  authenticated user info
  ├── /documents/*         upload, list, get, delete
  └── /questions/*         ask (RAG), list, get
        │
        ├── S3              file storage
        ├── SQS             document processing queue
        ├── PostgreSQL      app data (users, docs, questions)
        ├── pgvector        document chunk embeddings
        └── OpenAI          embeddings + chat completions
                │
                ▼
Lambda (SQS-triggered)
  └── document_processor   parse → chunk → embed → store
```

### Upload & Processing Flow

1. User uploads a PDF or TXT file to `POST /documents/upload`.
2. API saves the file to S3 and creates a document row with `status=processing`.
3. API sends a message to SQS with the `document_id`.
4. API returns immediately — the user does not wait for processing.
5. Lambda picks up the SQS message and runs the processing pipeline:
   - Downloads the file from S3.
   - Extracts text (PDF via `pypdf`, TXT via UTF-8 decode).
   - Splits text into chunks using LangChain `RecursiveCharacterTextSplitter`.
   - Creates embeddings via OpenAI `text-embedding-ada-002`.
   - Stores chunks and vectors in PostgreSQL (pgvector).
   - Updates document status to `ready` or `failed`.
6. Frontend polls `GET /documents/{id}` until status is `ready`.

### RAG Query Flow

1. User submits a question to `POST /questions/ask`.
2. API embeds the question using OpenAI.
3. API retrieves the top 5 nearest chunks from pgvector (filtered by user, optionally by course).
4. API sends the question + chunk context to `gpt-4o-mini`.
5. API persists the question, answer, and source references.
6. API returns the answer with source chunk previews.

## Project Structure

```text
backend/
├── app/
│   ├── main.py                 FastAPI app, CORS, router wiring
│   ├── core/
│   │   ├── config.py           pydantic-settings, env var loading
│   │   └── database.py         SQLAlchemy engine, session, Base
│   ├── middleware/
│   │   └── auth.py             Cognito JWT verification, get_current_user
│   ├── models/
│   │   ├── user.py             User (cognito_sub, email, display_name)
│   │   ├── course.py           Course (name, term) — FK placeholder only
│   │   ├── document.py         Document (s3_key, status, mime_type)
│   │   ├── document_chunk.py   DocumentChunk (text, embedding vector)
│   │   ├── question.py         Question (question_text, answer_text, model)
│   │   └── question_source.py  QuestionSource (chunk FK, relevance_score)
│   ├── routes/
│   │   ├── auth.py             /health, /me
│   │   ├── documents.py        /documents CRUD + upload
│   │   └── questions.py        /questions/ask, list, get
│   └── services/
│       ├── s3_service.py       S3 upload/download/delete
│       ├── sqs_service.py      SQS message sender
│       ├── embedding_service.py  LangChain OpenAI embeddings
│       ├── llm_service.py      LangChain OpenAI chat (RAG answers)
│       └── document_processor.py  full processing pipeline
├── lambda/
│   └── document_processor/
│       ├── handler.py          SQS-triggered Lambda entry point
│       └── requirements.txt    Lambda-specific dependencies
├── Dockerfile
└── requirements.txt
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | No | Health check |
| `GET` | `/me` | Yes | Current user info |
| `POST` | `/documents/upload` | Yes | Upload PDF/TXT, triggers SQS processing |
| `GET` | `/documents` | Yes | List user's documents (optional `?course_id=`) |
| `GET` | `/documents/{id}` | Yes | Get document details + processing status |
| `DELETE` | `/documents/{id}` | Yes | Delete document, S3 file, and chunks |
| `POST` | `/questions/ask` | Yes | Ask a question (RAG), returns answer + sources |
| `GET` | `/questions` | Yes | List previous questions (optional `?course_id=`) |
| `GET` | `/questions/{id}` | Yes | Get question with full answer and sources |

## Database Models

```text
users
  id (UUID PK)
  cognito_sub (unique, indexed)
  email
  display_name
  created_at

courses
  id (UUID PK)
  user_id (FK → users)
  name
  term
  created_at

documents
  id (UUID PK)
  user_id (FK → users)
  course_id (FK → courses, nullable)
  original_filename
  s3_key
  mime_type
  status (processing | ready | failed)
  error_message
  created_at

document_chunks
  id (UUID PK)
  document_id (FK → documents, indexed)
  chunk_text
  chunk_index
  embedding (vector 1536)
  token_count
  page_number
  created_at

questions
  id (UUID PK)
  user_id (FK → users)
  course_id (FK → courses, nullable)
  question_text
  answer_text
  model_used
  created_at

question_sources
  id (UUID PK)
  question_id (FK → questions)
  document_chunk_id (FK → document_chunks)
  relevance_score
```

## Authentication

All endpoints except `/health` require a Cognito JWT access token:

```
Authorization: Bearer <cognito_access_token>
```

The middleware verifies the JWT signature against Cognito JWKS, validates the issuer and token_use, and creates a local user record on first login.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `AWS_REGION` | Yes | AWS region for S3, SQS |
| `S3_BUCKET_NAME` | Yes | S3 bucket for uploaded files |
| `SQS_QUEUE_URL` | Yes | SQS queue URL for processing jobs |
| `COGNITO_USER_POOL_ID` | Yes | Cognito User Pool ID |
| `COGNITO_CLIENT_ID` | Yes | Cognito App Client ID |
| `COGNITO_REGION` | No | Cognito region (defaults to `AWS_REGION`) |
| `LLM_API_KEY` | Yes | API key for embeddings and chat (currently an OpenAI key) |
| `CORS_ORIGINS` | No | Comma-separated allowed origins (default: `http://localhost:5173`) |

## Local Development

Run via Docker Compose from the project root:

```sh
docker compose up --build
```

API available at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

## Supported File Types

- `application/pdf` — parsed via pypdf
- `text/plain` — UTF-8 decoded

## Not Yet Implemented

- Course CRUD routes (course_id FK exists on documents and questions)
- Pagination on list endpoints
- Rate limiting
- Alembic migrations (dependency installed, not configured)
- DOCX support (dependency installed, parser not wired)
- Admin endpoints for failed job monitoring
