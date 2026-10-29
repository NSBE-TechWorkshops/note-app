# Note Buddy Terraform

This directory uses Terraform to provision the AWS infrastructure for the Note
Buddy prototype. The "What each service does" section below explains each piece.

## Included

- VPC with two public and two private subnets, an internet gateway, and a NAT gateway
- Public ALB and ECS/Fargate backend service
- Private, single-AZ RDS PostgreSQL instance
- S3 upload bucket with public access blocked
- SQS document processing queue with a dead letter queue
- Lambda document processor, triggered by the queue
- ECR repositories for the backend and Lambda images, with image scanning and lifecycle cleanup
- Cognito User Pool and Hosted UI
- Optional Google identity provider
- Secrets Manager database credentials and optional LLM API key
- SSM application configuration parameters
- CloudWatch backend logs
- AWS Budget alerts

ECS tasks run in the public subnets with public IPs, and their security group
only permits application traffic from the ALB. The Lambda runs in the private
subnets and reaches the internet (for OpenAI) through the NAT gateway. RDS
remains private and only accepts PostgreSQL traffic from ECS and the Lambda.

This is a disposable prototype environment: destroying the Terraform stack
also deletes all objects in the upload bucket, including versioned objects,
and all images in the ECR repository. Do not use these cleanup settings for
production data.

## What each service does

If you are new to AWS, this section explains why each piece exists and how a
request moves through them. The Terraform files are named after the service they
create, so `s3.tf` is the bucket, `sqs.tf` is the queue, and so on.

### Networking: VPC, subnets, security groups (`vpc.tf`, `security_groups.tf`)

A VPC is your own private network inside AWS. It is split into subnets. Public
subnets have a route to the internet through the internet gateway. Private
subnets do not, so anything placed there can't be reached from outside.

Resources in a private subnet sometimes still need to call out, for example the
Lambda calling the OpenAI API. The NAT gateway handles that: it lets private
resources start outbound connections without letting anything connect in. It
also costs money while it runs, which is why this stack is meant to be torn down
when you're done.

Security groups are firewalls attached to individual resources. Each one lists
who may connect and on which port. The ALB accepts HTTP from anywhere, the
backend accepts traffic only from the ALB, and the database accepts connections
only from the backend and the Lambda. That chain means nobody can reach the
database directly.

### Entry point: Application Load Balancer (`alb.tf`)

The ALB is the public front door. The browser talks to the ALB, and the ALB
forwards each request to a healthy backend container. It checks a health
endpoint to know which containers are working. In a bigger deployment it is also
what lets you run several copies of the backend behind one address.

### Backend: ECR and ECS/Fargate (`ecr.tf`, `ecs.tf`)

ECR is a registry for Docker images, like Docker Hub but private to your account.
You build the backend image and push it here. There is a second repository for
the Lambda image.

ECS runs containers, and Fargate means AWS manages the servers for you. You
describe the container in a task definition (image, CPU, memory, environment),
and the ECS service keeps the requested number of copies running, restarting any
that crash. This is where the FastAPI app lives.

### Sign-in: Cognito (`cognito.tf`)

Cognito handles users so the app doesn't store passwords. The Hosted UI is a
login page AWS provides. With the optional Google provider turned on, users sign
in with Google, and Cognito hands the frontend signed JWT tokens. The backend
verifies those tokens to know who is making each request.

### File storage: S3 (`s3.tf`)

S3 stores the files students upload. Public access is blocked, objects are
encrypted at rest, and versioning is on. The files are never served directly to
the browser. The backend writes them and the Lambda reads them.

### Job queue: SQS and the dead letter queue (`sqs.tf`)

Reading a PDF, splitting it, and creating embeddings can take a while, so the
upload request doesn't wait for it. Instead the backend puts a small message on
an SQS queue saying which document to process, then returns right away.

If processing a message fails, SQS makes it available again. After three failed
attempts it moves the message to the dead letter queue, where it stays for 14
days so you can inspect it instead of retrying forever.

### Document processor: Lambda (`lambda.tf`)

Lambda runs a function only when something triggers it, and you pay only while it
runs. Here, a new SQS message triggers the function, one message at a time. It
downloads the file from S3, extracts the text, chunks it, gets embeddings from
OpenAI, and writes the chunks and vectors to the database. It then marks the
document `ready` or `failed`.

### Database: RDS PostgreSQL with pgvector (`rds.tf`)

RDS is managed PostgreSQL. AWS handles backups and patching. It holds users,
documents, and questions, and with the pgvector extension it also stores the
embedding vectors, which lets the backend search for the chunks closest in
meaning to a question. It is single-AZ here to keep costs down, which means no
automatic failover.

### Secrets and settings: Secrets Manager and SSM (`rds.tf`, `parameters.tf`)

Secrets Manager holds sensitive values, such as the generated database password
and the optional LLM API key. SSM Parameter Store holds non-secret configuration
like the bucket name, queue URL, and model names. Keeping both out of the code
means the images contain no credentials.

### Permissions: IAM (`iam.tf`)

IAM decides what each piece is allowed to do. The ECS task role may read and
write the S3 bucket and send messages to the queue. The Lambda role may receive
messages from the queue and read from the bucket. Neither gets more than it
needs. If a service gets an "access denied" error, the cause is usually a
missing line here.

### Monitoring and cost: CloudWatch and Budgets (`logs.tf`, `budget.tf`)

CloudWatch collects the backend's logs so you can debug without logging into a
container. AWS Budgets emails you when forecasted or actual spending crosses the
limit you set, which is worth having on any student account.

## Prerequisites

- Terraform >= 1.6
- AWS credentials with permission to create the resources in this directory
- A backend image pushed to ECR before the ECS service starts successfully

## Deploy

```sh
cd infra
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

Build and push the backend image using the `ecr_repository_url` output, then
apply again if the image tag or ECS task definition changes.

## Container image architecture

The ECS task definition pins `runtime_platform` to `ARM64`, so the image in ECR
**must** be `linux/arm64`. On an Apple Silicon machine a plain `docker build`
produces that natively. From an x86 machine, build with
`docker buildx build --platform linux/arm64`.

If the two disagree, tasks never start and the ALB returns `503` with no CORS
headers on every route, which surfaces in the browser as a CORS error rather
than as the architecture mismatch it actually is. The real cause is only
visible in the ECS service events:

```
CannotPullContainerError: image Manifest does not contain descriptor
matching platform 'linux/amd64'
```

To switch the stack to x86 instead, change `cpu_architecture` to `X86_64` in
`ecs.tf` and rebuild the image for `linux/amd64`. Change both together.

The database secret is created by Terraform and its ARN is available from
`rds_database_secret_arn`. Terraform state contains generated database and
optional application secrets, so use an encrypted remote state backend before
sharing this deployment.

## Cognito Google Login

Google federation is disabled by default. To enable it:

1. Create a Google OAuth web client in Google Cloud Console.
2. Add the Cognito callback URL to Google's authorized redirect URIs:
   `https://<cognito-domain>.auth.<region>.amazoncognito.com/oauth2/idpresponse`.
3. Set `enable_google_identity_provider`, `google_client_id`, and
   `google_client_secret` in an ignored `terraform.tfvars` file.
4. Apply Terraform and use `cognito_hosted_ui_login_url` for the frontend login
   redirect.

The frontend and backend do not need Google-specific libraries. Cognito's
Hosted UI handles the Google login and returns Cognito tokens.

## pgvector

The RDS instance is PostgreSQL and is provisioned for the application data.
Run this migration after the database is reachable:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Deferred Resources

SES, frontend hosting, HTTPS certificates, and autoscaling are intentionally not
included in this prototype scaffold.
