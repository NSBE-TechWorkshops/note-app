# Dead Letter Queue for failed document processing jobs
resource "aws_sqs_queue" "document_processor_dlq" {
  name                      = "${local.name_prefix}-doc-processor-dlq"
  message_retention_seconds = 1209600 # 14 days
}

# Main queue for document processing
resource "aws_sqs_queue" "document_processor" {
  name                       = "${local.name_prefix}-doc-processor"
  visibility_timeout_seconds = 300   # 5 min — must exceed Lambda timeout
  message_retention_seconds  = 86400 # 1 day

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.document_processor_dlq.arn
    maxReceiveCount     = 3
  })
}
