import json
import uuid

import pytest

from app.core.config import settings
from app.services import sqs_service


class FakeSqsClient:
    def __init__(self):
        self.sent = []

    def send_message(self, **kwargs):
        self.sent.append(kwargs)


def test_does_nothing_when_queue_url_is_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "sqs_queue_url", "")
    monkeypatch.setattr(sqs_service.boto3, "client", lambda *a, **k: pytest.fail("SQS must not be called"))

    sqs_service.send_process_document_message(uuid.uuid4())


def test_sends_the_document_id_to_the_configured_queue(monkeypatch):
    fake = FakeSqsClient()
    document_id = uuid.uuid4()
    monkeypatch.setattr(settings, "sqs_queue_url", "https://sqs.us-east-1.amazonaws.com/123/doc-processor")
    monkeypatch.setattr(sqs_service.boto3, "client", lambda service, **kwargs: fake)

    sqs_service.send_process_document_message(document_id)

    assert len(fake.sent) == 1
    assert fake.sent[0]["QueueUrl"] == "https://sqs.us-east-1.amazonaws.com/123/doc-processor"
    assert json.loads(fake.sent[0]["MessageBody"]) == {"document_id": str(document_id)}
