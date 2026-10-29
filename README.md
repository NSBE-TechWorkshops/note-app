# Note Buddy

Note Buddy lets you upload your notes and ask questions about them. It is a RAG app that I created using React & TanStack for the frontend and a FastAPI backend, running on AWS.

## Why I built this

I had two reasons.

The first was to learn how the pieces of a cloud system connect when you build an AI pipeline. A RAG app touches a lot of them: auth through Cognito, file storage in S3, a queue in SQS, a Lambda that processes documents, Postgres with pgvector for embeddings, and an LLM API at the end. Containers on ECS/Fargate, a load balancer, and Terraform tie it all together. I wanted to wire these up myself and see where each handoff breaks.

The second was a problem I actually have. My notes are scattered, and I wanted one place to put them all and ask about them when I need something specific, instead of searching through files and hoping I remember where I wrote it down. Note Buddy answers from my own notes and shows which chunks the answer came from.

## How it works

Students upload notes or course materials, ask questions, and get LLM answers grounded in what they uploaded. The architecture is meant to be simple enough to build and debug, with room to split services later.

### Stack

- Frontend: React with TanStack tools
- Backend: Python with FastAPI on ECS/Fargate
- Infrastructure: AWS, defined with Terraform
- File storage: Amazon S3
- Job queue and processing: SQS and a Lambda function
- Database: Amazon RDS for PostgreSQL, with pgvector for embeddings
- Authentication: Amazon Cognito with Google OAuth
- LLM and embeddings: OpenAI (`gpt-4o-mini` for answers)

### System overview

![Note Buddy system architecture](docs/architecture.png)

The numbers in the diagram match the steps below.

### User flow

1. A student signs in with Google through Cognito, and the frontend receives Cognito tokens.
2. The frontend sends API requests to FastAPI with the access token. FastAPI verifies it and identifies the user.
3. The student uploads a PDF or TXT file. FastAPI stores it in S3, creates a document record in PostgreSQL with status `processing`, and puts a job on SQS. The request returns right away.
4. SQS triggers the Lambda. It downloads the file, extracts the text, splits it into chunks, creates embeddings, and stores the chunks and vectors in PostgreSQL. A job that fails three times goes to a dead letter queue.
5. The document status changes to `ready` (or `failed`). The frontend polls the document status endpoint until then.
6. The student asks a question. FastAPI embeds it, retrieves the 5 nearest chunks from pgvector for that user, sends them to the LLM, and returns an answer with source previews.

The frontend treats uploads as asynchronous jobs. A successful upload means the file was received, not that it is ready for questions yet.

### API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check (no auth) |
| `GET` | `/me` | Current user info |
| `POST` | `/documents/upload` | Upload a PDF or TXT file and start processing |
| `GET` | `/documents` | List your documents |
| `GET` | `/documents/{id}` | Document details and processing status |
| `DELETE` | `/documents/{id}` | Delete the document, its S3 file, and its chunks |
| `POST` | `/questions/ask` | Ask a question and get an answer with sources |
| `GET` | `/questions` | List previous questions |
| `GET` | `/questions/{id}` | A question with its full answer and sources |
| `POST` `GET` | `/chat/sessions`, `/chat/sessions/{id}` | Create, list, and read chat sessions |
| `POST` | `/chat/sessions/{id}/messages`, `/chat/messages` | Add messages to a chat |

Every endpoint except `/health` needs a Cognito access token in the `Authorization: Bearer` header. The backend verifies the signature against Cognito's JWKS, checks the issuer and token type, and creates a local user record on first login.

### Data model

PostgreSQL holds users, courses, documents, document chunks (text, position, and a 1536-dimension embedding vector), questions, question sources (which chunks backed an answer, with a relevance score), and chat sessions and messages. Courses exist in the schema but aren't wired into the API yet. The backend README has the full field list.

### Storage and vector search

The S3 bucket is private. The backend reads and writes files with IAM permissions, and the frontend never gets public URLs for private notes.

pgvector keeps vectors in the same database as everything else. That means one thing to run, simpler backups and local development, and enough performance for early student-note datasets. Options like Qdrant, Pinecone, Chroma Cloud, Amazon S3 Vectors, or OpenSearch Serverless are worth a look only if retrieval gets slow, the vector volume grows, or filtering needs get more advanced.

### Ideas for later

- Pre-signed URLs for direct browser uploads
- An admin view for failed jobs
- Per-course retrieval filters
- Source citations with page numbers
- Hybrid search that combines keyword and vector search
- An evaluation set for answer quality
- Rate limits, usage tracking, and cost monitoring per user or course
- Transactional email through SES
- Moving high-throughput pieces to Go if needed

For more detail, see [backend/README.md](backend/README.md) and [infra/README.md](infra/README.md).

## Project layout

```text
frontend/   React + Vite + TanStack Query/Router
backend/    FastAPI API service and the Lambda document processor
infra/      Terraform for the AWS infrastructure
```

## Running it locally

The local stack runs the frontend, the backend, and a Postgres container with pgvector. Auth, file storage, queueing, and the LLM still call real AWS and OpenAI services, so you need an AWS account and an OpenAI key. Provision the AWS side first (see "Deploying to AWS" below) and use its outputs for the values in step 3.

### Prerequisites

- Docker and Docker Compose
- AWS credentials in `~/.aws` (the compose file mounts this into the backend container)
- An OpenAI API key
- Terraform 1.6 or newer, if you are provisioning the AWS resources yourself

### Steps

1. Clone the repo and move into it.

   ```sh
   git clone <repo-url>
   cd note-buddy
   ```

2. Create the backend env file.

   ```sh
   cp backend/env.example backend/.env
   ```

3. Fill in the blank values in `backend/.env`: `S3_BUCKET_NAME`, `SQS_QUEUE_URL`, `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `COGNITO_REGION`, and `LLM_API_KEY`. Add AWS keys there too if you are not relying on the mounted `~/.aws` profile. `DATABASE_URL` and `CORS_ORIGINS` already point at the compose services.

4. Create the frontend env file.

   ```sh
   cp frontend/.env.example frontend/.env
   ```

5. Fill in `VITE_COGNITO_USER_POOL_ID`, `VITE_COGNITO_CLIENT_ID`, and `VITE_COGNITO_DOMAIN` in `frontend/.env`. The API URL and redirect URIs default to localhost.

6. Start everything.

   ```sh
   docker compose up --build
   ```

7. Open the app at http://localhost:5173 and sign in through the Cognito Hosted UI.

Other local endpoints:

- Backend API: http://localhost:8000
- Health check: http://localhost:8000/health
- PostgreSQL with pgvector: localhost:5432

### Tests and linting

Backend tests use pytest and linting uses Ruff. Run them from `backend/` with the dependencies from `requirements.txt` installed. The integration tests need a Postgres database with pgvector, so with the compose `db` service running, create a test database and point `TEST_DATABASE_URL` at it:

```sh
cd backend
TEST_DATABASE_URL=postgresql://notebuddy:notebuddy@localhost:5432/notebuddy_test pytest
ruff check app lambda tests
```

The frontend type check and build run with `npm run build` from `frontend/`.

## Deploying to AWS

Terraform in `infra/` creates the VPC, ALB, ECS/Fargate service, RDS Postgres, S3 bucket, SQS queue, Lambda, Cognito, ECR, and the supporting pieces.

1. Copy the example variables and edit them.

   ```sh
   cd infra
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Create the infrastructure.

   ```sh
   terraform init
   terraform plan -out=tfplan
   terraform apply tfplan
   ```

3. Build the backend image and push it to the ECR repository from the `ecr_repository_url` output. The ECS task is pinned to ARM64, so the image has to be `linux/arm64`. On an x86 machine, build with `docker buildx build --platform linux/arm64`.

4. Apply again if the image tag or task definition changed.

5. To use Google sign-in, follow the Cognito Google Login steps in [infra/README.md](infra/README.md).

This is a disposable prototype setup. `terraform destroy` also deletes everything in the upload bucket and ECR repository, so don't point it at data you care about.
