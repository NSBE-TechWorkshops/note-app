"""AWS Lambda handler for SQS-triggered document processing."""

import json
import uuid


def lambda_doc_handler(event, context):
    """Process SQS messages containing document_id to process."""
    # Lambda needs these env vars: DATABASE_URL, AWS_REGION, S3_BUCKET_NAME, OPENAI_API_KEY
    # Set via Lambda configuration or Terraform

    # Lazy imports so module-level config reads env vars at cold start
    from app.services.document_processor import process_document

    failed = []
    for record in event.get("Records", []):
        body = json.loads(record["body"])
        document_id = uuid.UUID(body["document_id"])
        try:
            process_document(document_id)
        except Exception as exc:
            print(f"Failed to process document {document_id}: {exc}")
            failed.append(record["messageId"])

    # Report failures for SQS retry / DLQ
    if failed:
        return {"batchItemFailures": [{"itemIdentifier": mid} for mid in failed]}
    return {"batchItemFailures": []}
