# Terraform Infrastructure Build Brief

## Purpose

This document is a reference for building the AWS infrastructure for a student-notes RAG prototype using Terraform.

The goal is to create a small, deployable AWS environment for:

- React frontend
- FastAPI backend on ECS/Fargate
- Cognito Google authentication
- S3 document uploads
- RDS PostgreSQL with pgvector
- SES transactional email
- CloudWatch logging
- IAM roles and security groups

The first version should optimize for a working prototype by Thursday, September 24, 2026, not perfect production architecture.

## Preferred Terraform Layout

Start with a simple file layout rather than deeply nested modules.

```text
infra/
  providers.tf
  versions.tf
  variables.tf
  outputs.tf

  vpc.tf
  security_groups.tf
  iam.tf
  ecr.tf
  ecs.tf
  alb.tf
  rds.tf
  s3.tf
  cognito.tf
  ses.tf
  logs.tf
  parameters.tf
  budget.tf
```

Modules can be introduced later if the project grows.

## AWS Region

Use one primary region for the prototype.

Suggested default:

```text
us-east-1
```

Make the region configurable with a Terraform variable.

## Core Infrastructure

### VPC

Create a small VPC with:

- 2 public subnets across 2 availability zones
- 2 private subnets across 2 availability zones
- internet gateway
- route tables

For a cost-conscious prototype, avoid NAT Gateway if possible because it adds a steady monthly cost.

If ECS tasks in private subnets need outbound internet for LLM APIs, package downloads, or AWS APIs, one of these is required:

- NAT Gateway, simplest but more expensive
- public subnet ECS tasks with locked-down security groups, cheaper but less ideal
- VPC endpoints for AWS services plus another outbound path for third-party LLM APIs

Prototype recommendation:

- Put the public Application Load Balancer in public subnets.
- Decide whether ECS tasks run in public subnets or private subnets based on cost tolerance.
- For fastest prototype, public subnet ECS tasks with security group access only from ALB may be acceptable.

### Security Groups

Create security groups for:

- ALB
- ECS backend service
- RDS PostgreSQL

Rules:

- ALB allows inbound HTTP/HTTPS from internet.
- ECS allows inbound traffic only from ALB security group.
- RDS allows inbound PostgreSQL only from ECS security group.
- ECS allows outbound HTTPS for AWS APIs and LLM provider calls.

### ECR

Create one ECR repository for the FastAPI backend image.

Recommended:

- image scanning enabled if available
- lifecycle policy to expire old untagged images

### ECS/Fargate

Create:

- ECS cluster
- Fargate task definition
- ECS service
- CloudWatch log group
- IAM task execution role
- IAM task role for app permissions

Initial task sizing:

```text
CPU: 0.5 vCPU
Memory: 1GB or 2GB
Desired count: 1
```

If document parsing is memory-heavy, start with 1 vCPU and 2GB memory.

The FastAPI service should receive configuration through environment variables and SSM Parameter Store or Secrets Manager.

### Application Load Balancer

Create:

- public ALB
- target group for ECS service
- listener on HTTP
- optional HTTPS listener when a domain/certificate is available

For a fast prototype, HTTP may be acceptable only if no sensitive real user data is used. For any real student data, use HTTPS.

### RDS PostgreSQL

Create a small PostgreSQL instance.

Prototype recommendations:

- Single-AZ
- smallest practical instance class
- 20GB allocated storage
- encrypted storage enabled
- deletion protection disabled only for disposable prototype environments
- backups enabled with short retention, such as 1-7 days

The database must support the pgvector extension.

The app or migration process should run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Store database credentials in Secrets Manager or SSM Parameter Store.

Cost-conscious option:

- Use SSM Parameter Store for basic prototype config.
- Use Secrets Manager later if secret rotation is needed.

### S3 Upload Bucket

Create a private S3 bucket for uploaded student documents.

Recommended settings:

- block all public access
- server-side encryption enabled
- versioning optional for prototype
- lifecycle policy optional
- CORS only if browser direct uploads are used

Suggested object key pattern:

```text
uploads/{user_id}/{document_id}/{filename}
```

The ECS task role should have least-privilege access to this bucket.

### Cognito

Create:

- Cognito User Pool
- User Pool App Client
- Hosted UI domain
- Google identity provider
- callback/logout URLs for local and deployed frontend

The frontend will redirect users to Cognito Hosted UI for Google login.

FastAPI will verify Cognito JWTs.

Terraform should expose outputs for:

- Cognito user pool ID
- Cognito app client ID
- Cognito issuer URL
- Cognito hosted UI domain
- AWS region

Google OAuth credentials may need to be created manually in Google Cloud Console, then passed into Terraform as sensitive variables.

### SES

Set up SES for transactional email.

Prototype options:

- Verify a single sender email address.
- Later, verify a full domain.

If SES remains in sandbox mode, emails can only be sent to verified recipients. For real signups, request production access.

Use SES for:

- registration emails if needed
- email verification if not fully handled by Cognito
- password/reset notifications if needed

### CloudWatch Logs

Create log groups for:

- ECS FastAPI service
- optional future worker service

Set a retention period to control cost.

Suggested prototype retention:

```text
14 days
```

### SSM Parameter Store / Secrets

Recommended prototype config storage:

- SSM Parameter Store for non-secret config and low-risk secrets
- Secrets Manager for database password or API keys if preferred

Likely parameters:

```text
/student-rag/dev/database-url
/student-rag/dev/s3-bucket
/student-rag/dev/cognito-user-pool-id
/student-rag/dev/cognito-client-id
/student-rag/dev/cognito-issuer
/student-rag/dev/llm-provider
/student-rag/dev/embedding-model
/student-rag/dev/llm-api-key
```

Use secure string parameters for sensitive values.

### IAM

Create IAM roles with least privilege:

- ECS task execution role
  - pull from ECR
  - write CloudWatch logs

- ECS task role
  - read/write required S3 upload bucket paths
  - read required SSM parameters or Secrets Manager secrets
  - send email with SES if backend sends email directly

Avoid broad `*` permissions.

### Optional Budget

Create an AWS Budget for the prototype account or project.

Suggested budget:

```text
Monthly budget: $25-$50
Alert thresholds: 50%, 80%, 100%
```

This is especially useful because RDS, NAT Gateway, ALB, and LLM usage can create steady costs.

## Environment Variables For FastAPI

Terraform should make it easy to provide these to the ECS task:

```text
APP_ENV=dev
AWS_REGION=us-east-1
S3_UPLOAD_BUCKET=...
DATABASE_URL=...
COGNITO_USER_POOL_ID=...
COGNITO_CLIENT_ID=...
COGNITO_ISSUER=...
COGNITO_JWKS_URL=...
LLM_PROVIDER=...
EMBEDDING_MODEL=...
LLM_MODEL=...
```

Secrets should not be hardcoded into Terraform files.

## Terraform Outputs

Recommended outputs:

```text
alb_dns_name
backend_base_url
frontend_config_cognito_user_pool_id
frontend_config_cognito_client_id
frontend_config_cognito_domain
frontend_config_aws_region
s3_upload_bucket_name
rds_endpoint
ecs_cluster_name
ecs_service_name
ecr_repository_url
```

## Deployment Flow

Expected deployment flow:

1. Build FastAPI Docker image.
2. Push image to ECR.
3. Apply Terraform infrastructure.
4. Deploy ECS service using the ECR image.
5. Run database migrations.
6. Deploy React frontend with Cognito config and backend URL.
7. Test sign-in, upload, processing, and question answering.

## Future Infrastructure Additions

After the prototype works, add:

- SQS queue for ingestion jobs
- separate ECS worker service
- dead-letter queue for failed processing jobs
- autoscaling policies
- HTTPS certificate through ACM
- custom domain through Route 53
- WAF for public endpoints
- private ECS tasks plus NAT Gateway or VPC endpoints
- CI/CD pipeline
- separate dev/staging/prod environments
- more detailed observability and alerts

## Cost Notes

Highest-risk recurring costs for the prototype:

- RDS running 24/7
- NAT Gateway if used
- Application Load Balancer
- ECS/Fargate task size and uptime
- LLM and embedding API calls
- CloudWatch logs if verbose

Cost-conscious prototype choices:

- Single ECS service
- Single-AZ RDS
- pgvector in PostgreSQL instead of a separate vector database
- no NAT Gateway if acceptable
- short CloudWatch log retention
- AWS Budget alerts

## Non-Goals For MVP

Do not build these unless explicitly needed for the prototype:

- multi-region deployment
- Kubernetes
- complex Terraform module hierarchy
- separate worker service before the first demo works
- OpenSearch Serverless
- advanced autoscaling
- full CI/CD platform
- custom domain before basic deployment is healthy

