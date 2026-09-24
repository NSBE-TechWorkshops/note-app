output "aws_region" {
  description = "AWS region used by the deployment."
  value       = var.aws_region
}

output "alb_dns_name" {
  description = "Public DNS name of the backend ALB."
  value       = aws_lb.backend.dns_name
}

output "backend_base_url" {
  description = "HTTP base URL for the backend."
  value       = "http://${aws_lb.backend.dns_name}"
}

output "frontend_config_cognito_user_pool_id" {
  value = aws_cognito_user_pool.this.id
}

output "frontend_config_cognito_client_id" {
  value = aws_cognito_user_pool_client.this.id
}

output "frontend_config_cognito_domain" {
  value = "${aws_cognito_user_pool_domain.this.domain}.auth.${var.aws_region}.amazoncognito.com"
}

output "cognito_issuer_url" {
  value = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.this.id}"
}

output "s3_upload_bucket_name" {
  value = aws_s3_bucket.uploads.bucket
}

output "rds_endpoint" {
  value = aws_db_instance.this.address
}

output "rds_database_secret_arn" {
  value     = aws_secretsmanager_secret.database.arn
  sensitive = true
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.backend.name
}

output "ecs_service_name" {
  value = aws_ecs_service.backend.name
}

output "ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecr_lambda_repository_url" {
  value = aws_ecr_repository.lambda_doc_processor.repository_url
}

output "sqs_queue_url" {
  value = aws_sqs_queue.document_processor.url
}

output "sqs_dlq_url" {
  value = aws_sqs_queue.document_processor_dlq.url
}

output "cognito_hosted_ui_login_url" {
  value = "https://${aws_cognito_user_pool_domain.this.domain}.auth.${var.aws_region}.amazoncognito.com/login?client_id=${aws_cognito_user_pool_client.this.id}&response_type=code&scope=openid+email+profile&redirect_uri=${urlencode(var.cognito_callback_urls[0])}"
}
