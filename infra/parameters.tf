resource "aws_ssm_parameter" "s3_bucket" {
  name  = "/${local.name_prefix}/s3-bucket"
  type  = "String"
  value = aws_s3_bucket.uploads.bucket
}

resource "aws_ssm_parameter" "cognito_user_pool_id" {
  name  = "/${local.name_prefix}/cognito-user-pool-id"
  type  = "String"
  value = aws_cognito_user_pool.this.id
}

resource "aws_ssm_parameter" "cognito_client_id" {
  name  = "/${local.name_prefix}/cognito-client-id"
  type  = "String"
  value = aws_cognito_user_pool_client.this.id
}

resource "aws_ssm_parameter" "cognito_issuer" {
  name  = "/${local.name_prefix}/cognito-issuer"
  type  = "String"
  value = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.this.id}"
}

resource "aws_ssm_parameter" "llm_provider" {
  name  = "/${local.name_prefix}/llm-provider"
  type  = "String"
  value = var.llm_provider
}

resource "aws_ssm_parameter" "embedding_model" {
  name  = "/${local.name_prefix}/embedding-model"
  type  = "String"
  value = var.embedding_model
}

resource "aws_ssm_parameter" "llm_model" {
  name  = "/${local.name_prefix}/llm-model"
  type  = "String"
  value = var.llm_model
}
