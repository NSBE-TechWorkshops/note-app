# Document processor Lambda function (container image)
resource "aws_lambda_function" "doc_processor" {
  function_name = "${local.name_prefix}-doc-processor"
  role          = aws_iam_role.lambda_doc_processor.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.lambda_doc_processor.repository_url}:${var.lambda_image_tag}"
  timeout       = 120
  memory_size   = 1024

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = merge(
      {
        AWS_REGION_NAME = var.aws_region
        S3_BUCKET_NAME  = aws_s3_bucket.uploads.bucket
        DATABASE_SECRET = aws_secretsmanager_secret.database.arn
        LLM_PROVIDER    = var.llm_provider
        EMBEDDING_MODEL = var.embedding_model
        LLM_MODEL       = var.llm_model
      },
      var.llm_api_key != null ? { APP_SECRET = aws_secretsmanager_secret.application[0].arn } : {}
    )
  }

  depends_on = [aws_iam_role_policy.lambda_doc_processor]
}

# SQS trigger
resource "aws_lambda_event_source_mapping" "doc_processor_sqs" {
  event_source_arn = aws_sqs_queue.document_processor.arn
  function_name    = aws_lambda_function.doc_processor.arn
  batch_size       = 1
  enabled          = true
}
