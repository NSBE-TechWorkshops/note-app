# Note Buddy Terraform

This directory provisions the backend prototype infrastructure described in
`../INFRA_TERRAFORM_README.md`.

## Included

- VPC with two public and two private subnets
- Public ALB and ECS/Fargate backend service
- Private, single-AZ RDS PostgreSQL instance
- S3 upload bucket with public access blocked
- ECR backend repository with image scanning and lifecycle cleanup
- Cognito User Pool and Hosted UI
- Optional Google identity provider
- Secrets Manager database credentials and optional LLM API key
- SSM application configuration parameters
- CloudWatch backend logs
- AWS Budget alerts

ECS tasks use public subnets and public IPs to avoid a NAT Gateway during the
prototype. Their security group only permits application traffic from the ALB.
RDS remains private and only accepts PostgreSQL traffic from ECS.

This is a disposable prototype environment: destroying the Terraform stack
also deletes all objects in the upload bucket, including versioned objects,
and all images in the ECR repository. Do not use these cleanup settings for
production data.

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

SES, frontend hosting, HTTPS certificates, NAT Gateway, SQS, workers, and
autoscaling are intentionally not included in this prototype scaffold.
