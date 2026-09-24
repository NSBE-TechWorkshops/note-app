import json
import uuid

import boto3

from app.core.config import settings

def send_process_document_message(document_id: uuid.UUID) -> None:
    """Send a document processing job to SQS."""
    if not settings.sqs_queue_url:
        # ponytail: no-op when SQS_QUEUE_URL is unset; wire up queue when document processing is needed
        return
    client = boto3.client("sqs", region_name=settings.aws_region)
    client.send_message(
        QueueUrl=settings.sqs_queue_url,
        MessageBody=json.dumps({"document_id": str(document_id)}),
    )
