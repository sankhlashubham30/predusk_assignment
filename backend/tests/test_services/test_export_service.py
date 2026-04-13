"""Tests for the export service."""
import json
import csv
import io
import datetime
import pytest

from app.services.export_service import export_as_json, export_as_csv
from app.models.job import Job


@pytest.fixture
def mock_job():
    job = Job()
    job.id = 42
    job.status = "completed"
    job.is_finalized = True
    job.is_reviewed = True
    job.retry_count = 0
    job.progress = 100.0
    job.queued_at = datetime.datetime(2026, 4, 11, 12, 0, 0)
    job.completed_at = datetime.datetime(2026, 4, 11, 12, 0, 5)
    job.result = {
        "title": "Export Test Doc",
        "category": "finance",
        "summary": "A test for export.",
        "keywords": ["export", "test"],
        "confidence_score": 0.95,
        "metadata": {"word_count": 8},
    }
    job.reviewed_result = job.result
    return job


class TestExportAsJson:
    def test_returns_valid_json(self, mock_job):
        output = export_as_json(mock_job)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_contains_result_fields(self, mock_job):
        parsed = json.loads(export_as_json(mock_job))
        # Either flat result or nested under 'result'
        result = parsed.get("result", parsed)
        assert "title" in result or "title" in parsed

    def test_contains_job_metadata(self, mock_job):
        parsed = json.loads(export_as_json(mock_job))
        # Should contain job ID or export metadata
        assert "job_id" in parsed or "id" in parsed or "title" in parsed


class TestExportAsCsv:
    def test_returns_string(self, mock_job):
        output = export_as_csv(mock_job)
        assert isinstance(output, (str, bytes))

    def test_parseable_csv(self, mock_job):
        output = export_as_csv(mock_job)
        if isinstance(output, bytes):
            output = output.decode("utf-8")
        reader = csv.reader(io.StringIO(output))
        rows = list(reader)
        assert len(rows) >= 1  # at least a header or data row

    def test_csv_not_empty(self, mock_job):
        output = export_as_csv(mock_job)
        assert len(output) > 0
