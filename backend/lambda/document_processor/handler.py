"""AWS Lambda handler for SQS-triggered document processing."""

import json
import os
import uuid


def _load_secrets():
    """Load DATABASE_URL and OPENAI_API_KEY from Secrets Manager at cold start."""
    if os.environ.get("DATABASE_URL"):
        return  # Already loaded

    import boto3
    client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION_NAME", "us-east-1"))

    # Database secret
    db_secret_arn = os.environ.get("DATABASE_SECRET")
    if db_secret_arn:
        resp = client.get_secret_value(SecretId=db_secret_arn)
        secret = json.loads(resp["SecretString"])
        os.environ["DATABASE_URL"] = secret["database_url"]

    # LLM API key secret
    app_secret_arn = os.environ.get("APP_SECRET")
    if app_secret_arn:
        resp = client.get_secret_value(SecretId=app_secret_arn)
        secret = json.loads(resp["SecretString"])
        if "llm_api_key" in secret:
            os.environ["OPENAI_API_KEY"] = secret["llm_api_key"]


def lambda_doc_handler(event, context):
    """Process SQS messages containing document_id to process."""
    _load_secrets()

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
