"""Cheap checks that the Terraform and the application code still agree with each other."""

import re
from pathlib import Path

import pytest

INFRA = Path(__file__).resolve().parents[2] / "infra"


def number_after(filename: str, key: str) -> int:
    match = re.search(rf"^\s*{key}\s*=\s*(\d+)", (INFRA / filename).read_text(), re.MULTILINE)
    assert match, f"{key} not found in {filename}"
    return int(match.group(1))


def test_queue_visibility_timeout_exceeds_lambda_timeout():
    # If the Lambda can run longer than the visibility timeout, SQS hands the same job to a second worker.
    assert number_after("sqs.tf", "visibility_timeout_seconds") > number_after("lambda.tf", "timeout")


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known gap: the handler returns batchItemFailures, but the SQS trigger in lambda.tf doesn't enable "
        "function_response_types = [\"ReportBatchItemFailures\"], so caught errors are treated as success and "
        "never retried or sent to the DLQ. Remove this marker once lambda.tf is fixed."
    ),
)
def test_lambda_trigger_reports_partial_batch_failures():
    assert "ReportBatchItemFailures" in (INFRA / "lambda.tf").read_text()
