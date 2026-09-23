variable "aws_region" {
  description = "AWS region for the prototype."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short project name used in AWS resource names."
  type        = string
  default     = "note-buddy"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR range for the application VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "container_image_tag" {
  description = "ECR image tag deployed by ECS. Push this tag before applying ECS changes."
  type        = string
  default     = "latest"
}

variable "container_port" {
  description = "Port exposed by the FastAPI container."
  type        = number
  default     = 8000
}

variable "ecs_cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 512
}

variable "ecs_memory" {
  description = "Fargate task memory in MiB."
  type        = number
  default     = 1024
}

variable "ecs_desired_count" {
  description = "Number of backend ECS tasks."
  type        = number
  default     = 1
}

variable "health_check_path" {
  description = "ALB health check path."
  type        = string
  default     = "/health"
}

variable "db_name" {
  description = "PostgreSQL database name."
  type        = string
  default     = "notebuddy"
}

variable "db_username" {
  description = "PostgreSQL master username."
  type        = string
  default     = "notebuddy"
}

variable "db_instance_class" {
  description = "Small RDS instance class for the prototype."
  type        = string
  default     = "db.t3.micro"
}

variable "db_engine_version" {
  description = "PostgreSQL engine version."
  type        = string
  default     = "16.3"
}

variable "db_backup_retention_days" {
  description = "RDS automated backup retention in days."
  type        = number
  default     = 3
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days."
  type        = number
  default     = 14
}

variable "cognito_callback_urls" {
  description = "Allowed Cognito Hosted UI callback URLs."
  type        = list(string)
  default     = ["http://localhost:5173/callback"]
}

variable "cognito_logout_urls" {
  description = "Allowed Cognito Hosted UI logout URLs."
  type        = list(string)
  default     = ["http://localhost:5173/"]
}

variable "cognito_domain_prefix" {
  description = "Globally unique Cognito Hosted UI domain prefix."
  type        = string
  default     = null
}

variable "enable_google_identity_provider" {
  description = "Create and enable the Google identity provider in Cognito."
  type        = bool
  default     = false
}

variable "google_client_id" {
  description = "Google OAuth client ID from Google Cloud Console."
  type        = string
  sensitive   = true
  default     = null
}

variable "google_client_secret" {
  description = "Google OAuth client secret from Google Cloud Console."
  type        = string
  sensitive   = true
  default     = null
}

variable "cors_origins" {
  description = "Comma-separated browser origins allowed by the backend."
  type        = string
  default     = "http://localhost:5173"
}

variable "llm_provider" {
  description = "LLM provider name passed to the backend."
  type        = string
  default     = "openai"
}

variable "embedding_model" {
  description = "Embedding model passed to the backend."
  type        = string
  default     = "text-embedding-3-small"
}

variable "llm_model" {
  description = "LLM model passed to the backend."
  type        = string
  default     = "gpt-4o-mini"
}

variable "llm_api_key" {
  description = "Optional LLM API key. Stored in Secrets Manager when provided."
  type        = string
  sensitive   = true
  default     = null
}

variable "budget_limit_usd" {
  description = "Monthly AWS budget limit in USD."
  type        = number
  default     = 50
}

variable "budget_alert_email" {
  description = "Email address for AWS Budget notifications."
  type        = string
  default     = "kylefrancisdev@gmail.com"
}
