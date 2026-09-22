# Student Notes RAG Project Architecture

## Purpose

This project is a prototype RAG application for students. Students can upload notes or course materials, then ask questions and receive LLM-generated answers grounded in their uploaded content.

The first version prioritizes getting a working prototype deployed quickly. The architecture should stay simple enough to build and debug, while leaving a clear path to split services later.

## Initial Technology Choices

- Frontend: React with TanStack tools
- Backend: Python with FastAPI
- Infrastructure: AWS
- Infrastructure as code: Terraform
- File storage: Amazon S3
- Database: Amazon RDS for PostgreSQL
- Vector storage: pgvector inside PostgreSQL
- Authentication: Amazon Cognito with Google OAuth
- Email: Amazon SES
- Backend runtime: ECS/Fargate
- LLM and embeddings: provider to be decided, likely OpenAI API or Amazon Bedrock

## High-Level Architecture

```text
React + TanStack frontend
  -> Cognito Google sign-in
  -> FastAPI backend on ECS/Fargate
    -> S3 for uploaded files
    -> RDS PostgreSQL for app data
    -> pgvector for document embeddings
    -> SES for transactional email
    -> LLM/embedding provider for RAG answers
```

## Core User Flow

1. A student signs in with Google through Cognito.
2. The frontend receives Cognito tokens.
3. The frontend sends API requests to FastAPI with the Cognito access token.
4. FastAPI verifies the token and identifies the user.
5. The student uploads notes or course documents.
6. FastAPI stores the original file in S3.
7. FastAPI creates a document record in PostgreSQL with status `processing`.
8. FastAPI processes the document in the background:
   - extract text
   - clean text
   - split text into chunks
   - create embeddings
   - store chunks and vectors in PostgreSQL using pgvector
9. The document status changes to `ready`.
10. The student asks a question.
11. FastAPI embeds the question, retrieves relevant chunks, sends context to the LLM, and returns an answer with sources.

## MVP Processing Model

For the prototype, document parsing and embedding can happen inside the FastAPI ECS service as a background task.

This keeps the first version simpler because there is no separate queue, worker service, or Lambda function to deploy.

The upload request should not wait for the entire RAG pipeline to finish. Instead:

```text
Upload file
  -> save to S3
  -> create document row with status = processing
  -> return response immediately
  -> background task parses/chunks/embeds
  -> update status = ready or failed
```

The frontend can poll a document status endpoint until the document is ready.

## Future Processing Model

After the prototype works, move parsing and embedding into a separate worker service.

```text
FastAPI upload endpoint
  -> S3
  -> PostgreSQL document row
  -> SQS job

Worker service
  -> reads SQS job
  -> downloads file from S3
  -> parses/chunks/embeds
  -> writes chunks and vectors to PostgreSQL
  -> updates document status
```

This improves reliability, retry behavior, and scaling. The same Python processing code can mostly be reused.

## Suggested Database Model

Exact schema can change, but the initial data model will likely need:

- `users`
  - Cognito subject ID
  - email
  - display name
  - created timestamp

- `courses`
  - owner user ID
  - course name
  - optional term or section

- `documents`
  - owner user ID
  - optional course ID
  - original filename
  - S3 object key
  - MIME type
  - processing status: `processing`, `ready`, `failed`
  - error message if failed
  - created timestamp

- `document_chunks`
  - document ID
  - chunk text
  - chunk index
  - embedding vector
  - token count
  - page number or source location if available

- `questions`
  - owner user ID
  - optional course ID
  - question text
  - answer text
  - model used
  - created timestamp

- `question_sources`
  - question ID
  - document chunk ID
  - relevance score

## API Surface

Likely MVP endpoints:

```text
GET    /health
GET    /me

POST   /documents/upload
GET    /documents
GET    /documents/{document_id}
DELETE /documents/{document_id}

POST   /ask
GET    /questions
GET    /questions/{question_id}

GET    /courses
POST   /courses
PATCH  /courses/{course_id}
DELETE /courses/{course_id}
```

## Authentication Approach

Use Cognito User Pools with Google as an identity provider.

Frontend flow:

```text
React app
  -> Cognito Hosted UI
  -> Google sign-in
  -> Cognito returns JWT tokens
  -> React calls FastAPI with Authorization: Bearer <access_token>
```

Backend responsibility:

- Verify Cognito JWT signature using Cognito JWKS.
- Validate issuer and audience/client ID.
- Extract Cognito subject and email.
- Create or update local user record in PostgreSQL.
- Enforce per-user access on documents, chunks, questions, and courses.

## File Storage

Use S3 for uploaded notes and documents.

Recommended key pattern:

```text
uploads/{user_id}/{document_id}/{original_filename}
```

Keep the bucket private. The backend should upload/download files using IAM permissions. The frontend should not receive public S3 object URLs for private notes.

If direct browser uploads are added later, use pre-signed upload URLs.

## Vector Store

Use pgvector in PostgreSQL for the MVP.

Benefits:

- One database for app data and vectors
- Lower architecture complexity
- Good enough for early student-note datasets
- Easier backups and local development

Possible future migration options:

- Qdrant
- Pinecone
- Chroma Cloud
- Amazon S3 Vectors
- OpenSearch Serverless

Do not migrate until there is a clear need, such as slow retrieval, high vector volume, or advanced filtering requirements.

## Frontend Notes

Use React with TanStack tools.

Likely frontend needs:

- Authenticated app shell
- Upload flow
- Document status display
- Course/document organization
- Question input
- Answer view with cited source chunks
- Previous questions/history

The frontend should treat uploaded documents as asynchronous jobs. A successful upload means the file was received, not that it is ready for Q&A yet.

## Deployment Plan For Prototype

Target deployment milestone: Thursday, September 24, 2026.

Recommended build order:

1. Create local FastAPI app with health check.
2. Add Cognito JWT verification.
3. Add PostgreSQL models and migrations.
4. Add S3 upload.
5. Add document parsing and chunking.
6. Add embeddings and pgvector storage.
7. Add `/ask` retrieval and LLM response.
8. Deploy FastAPI to ECS/Fargate.
9. Deploy React app.
10. Test full flow with one or two sample notes.

## Later Improvements

- Add SQS queue and separate worker service.
- Add retry handling for failed document ingestion.
- Add admin dashboard for failed jobs.
- Add per-course retrieval filters.
- Add source citations with page numbers.
- Add hybrid search, combining keyword search and vector search.
- Add evaluation set for answer quality.
- Add rate limits and usage tracking.
- Add cost monitoring per user or per course.
- Move high-throughput service pieces to Go if needed.

