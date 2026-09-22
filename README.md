# Note Buddy

Student notes RAG prototype with a React/TanStack frontend and FastAPI backend.

## Local Development

Run the full local stack:

```sh
docker compose up --build
```

Services:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Backend health check: http://localhost:8000/health
- PostgreSQL with pgvector: localhost:5432

## Project Layout

```text
frontend/   React + Vite + TanStack Query
backend/    FastAPI API service
infra/      Terraform infrastructure, added later
```

The backend container is the closest match to the planned ECS/Fargate deployment.
The frontend container is useful for consistent local development, though the
production frontend can later be deployed as static files to S3/CloudFront.
