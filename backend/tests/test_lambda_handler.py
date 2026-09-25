"""The Lambda handler lives outside the app package (backend/lambda/...), so load it by path."""

import importlib.util
import json
import uuid
from pathlib import Path

import pytest

from app.services import document_processor

HANDLER_PATH = Path(__file__).resolve().parents[1] / "lambda" / "document_processor" / "handler.py"


@pytest.fixture
def handler():
    spec = importlib.util.spec_from_file_location("doc_handler", HANDLER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.lambda_doc_handler


def sqs_record(message_id: str, document_id: uuid.UUID) -> dict:
    return {"messageId": message_id, "body": json.dumps({"document_id": str(document_id)})}


def test_processes_every_record_in_the_batch(handler, monkeypatch):
    processed = []
    monkeypatch.setattr(document_processor, "process_document", processed.append)
    ids = [uuid.uuid4(), uuid.uuid4()]

    result = handler({"Records": [sqs_record("m1", ids[0]), sqs_record("m2", ids[1])]}, None)

    assert processed == ids
    assert result == {"batchItemFailures": []}


def test_reports_only_the_failed_message(handler, monkeypatch):
    bad_id = uuid.uuid4()

    def fake_process(document_id):
        if document_id == bad_id:
            raise RuntimeError("boom")

    monkeypatch.setattr(document_processor, "process_document", fake_process)

    result = handler({"Records": [sqs_record("ok", uuid.uuid4()), sqs_record("bad", bad_id)]}, None)

    assert result == {"batchItemFailures": [{"itemIdentifier": "bad"}]}


def test_empty_event_is_a_no_op(handler):
    assert handler({}, None) == {"batchItemFailures": []}
