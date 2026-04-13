"""Tests for /api/v1/documents endpoints."""
import io
import json
import pytest
from unittest.mock import patch, MagicMock


class TestUpload:
    @patch("app.services.document_service.process_document")
    def test_upload_single_file(self, mock_task, client, sample_user, auth_headers):
        """Upload a single file — returns 202 with job details."""
        mock_task.delay.return_value = MagicMock(id="celery-task-abc")
        files = [("files", ("hello.txt", io.BytesIO(b"Hello DocFlow"), "text/plain"))]
        resp = client.post("/api/v1/documents/upload", files=files, headers=auth_headers)
        assert resp.status_code == 202
        data = resp.json()
        assert data["uploaded"] == 1
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["filename"] == "hello.txt"
        assert "job_id" in data["jobs"][0]

    @patch("app.services.document_service.process_document")
    def test_upload_multiple_files(self, mock_task, client, auth_headers):
        """Uploading multiple files creates multiple jobs."""
        mock_task.delay.return_value = MagicMock(id="celery-task-xyz")
        files = [
            ("files", ("a.txt", io.BytesIO(b"File A"), "text/plain")),
            ("files", ("b.txt", io.BytesIO(b"File B"), "text/plain")),
        ]
        resp = client.post("/api/v1/documents/upload", files=files, headers=auth_headers)
        assert resp.status_code == 202
        assert resp.json()["uploaded"] == 2

    def test_upload_no_files(self, client):
        """Uploading with empty file list returns 400."""
        resp = client.post("/api/v1/documents/upload", files=[])
        assert resp.status_code == 400

    @patch("app.services.document_service.process_document")
    def test_upload_without_auth(self, mock_task, client):
        """Upload works without auth (optional auth pattern)."""
        mock_task.delay.return_value = MagicMock(id="anon-task")
        files = [("files", ("anon.txt", io.BytesIO(b"anon content"), "text/plain"))]
        resp = client.post("/api/v1/documents/upload", files=files)
        assert resp.status_code == 202


class TestList:
    def test_list_empty(self, client, auth_headers):
        resp = client.get("/api/v1/documents/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_with_documents(self, client, auth_headers, completed_job):
        resp = client.get("/api/v1/documents/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        item = data["items"][0]
        assert "status" in item
        assert "original_filename" in item
        assert "progress" in item

    def test_list_filter_by_status(self, client, auth_headers, completed_job):
        resp = client.get("/api/v1/documents/?status=completed", headers=auth_headers)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["status"] == "completed"

    def test_list_search(self, client, auth_headers, completed_job):
        resp = client.get("/api/v1/documents/?search=sample", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_list_pagination(self, client, auth_headers, completed_job):
        resp = client.get("/api/v1/documents/?page=1&page_size=1", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 1
        assert "pages" in data


class TestDetail:
    def test_get_detail_success(self, client, auth_headers, completed_job):
        doc, job = completed_job
        resp = client.get(f"/api/v1/documents/{doc.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["document"]["id"] == doc.id
        assert data["job"]["status"] == "completed"
        assert data["job"]["result"] is not None

    def test_get_detail_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/documents/99999", headers=auth_headers)
        assert resp.status_code == 404


class TestReviewAndFinalize:
    def test_update_result(self, client, auth_headers, completed_job):
        doc, job = completed_job
        payload = {"reviewed_result": {"title": "Edited Title", "summary": "Edited summary"}}
        resp = client.put(f"/api/v1/documents/{doc.id}/result",
                          json=payload, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["job_id"] == job.id

    def test_update_result_on_incomplete_job(self, client, auth_headers, db, sample_user):
        import datetime
        from app.models.document import Document
        from app.models.job import Job
        doc = Document(
            original_filename="proc.txt", stored_filename="proc_s.txt",
            file_path="/tmp/proc_s.txt", file_size=10,
            file_type="txt", mime_type="text/plain", owner_id=sample_user.id,
        )
        db.add(doc); db.commit(); db.refresh(doc)
        job = Job(
            document_id=doc.id, status="processing", progress=50.0,
            current_step="document_parsing_started", retry_count=0,
            queued_at=datetime.datetime.utcnow(),
        )
        db.add(job); db.commit()
        resp = client.put(f"/api/v1/documents/{doc.id}/result",
                          json={"reviewed_result": {}}, headers=auth_headers)
        assert resp.status_code == 400

    def test_finalize_success(self, client, auth_headers, completed_job):
        doc, job = completed_job
        resp = client.post(f"/api/v1/documents/{doc.id}/finalize", headers=auth_headers)
        assert resp.status_code == 200

        # Verify it's locked — second finalize should still return 200 or be idempotent
        resp2 = client.post(f"/api/v1/documents/{doc.id}/finalize", headers=auth_headers)
        assert resp2.status_code in (200, 400)


class TestRetry:
    def test_retry_non_failed_job(self, client, auth_headers, completed_job):
        """Retrying a completed (not failed) job should return 400."""
        doc, job = completed_job
        resp = client.post(f"/api/v1/documents/{doc.id}/retry", headers=auth_headers)
        assert resp.status_code == 400

    @patch("app.services.document_service.process_document")
    def test_retry_failed_job(self, mock_task, client, auth_headers, db, sample_user):
        import datetime
        from app.models.document import Document
        from app.models.job import Job
        mock_task.delay.return_value = MagicMock(id="retry-task-id")
        doc = Document(
            original_filename="fail.txt", stored_filename="fail_s.txt",
            file_path="/tmp/fail_s.txt", file_size=5,
            file_type="txt", mime_type="text/plain", owner_id=sample_user.id,
        )
        db.add(doc); db.commit(); db.refresh(doc)
        job = Job(
            document_id=doc.id, status="failed", progress=0.0,
            current_step="job_failed", retry_count=0,
            error_message="Simulated failure",
            queued_at=datetime.datetime.utcnow(),
        )
        db.add(job); db.commit()
        resp = client.post(f"/api/v1/documents/{doc.id}/retry", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["retry_count"] == 1


class TestExport:
    def test_export_json(self, client, auth_headers, completed_job):
        doc, job = completed_job
        resp = client.get(f"/api/v1/documents/{doc.id}/export?format=json",
                          headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"
        data = resp.json()
        assert "title" in data or "result" in data  # flexible schema

    def test_export_csv(self, client, auth_headers, completed_job):
        doc, job = completed_job
        resp = client.get(f"/api/v1/documents/{doc.id}/export?format=csv",
                          headers=auth_headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert len(resp.content) > 0

    def test_export_invalid_format(self, client, auth_headers, completed_job):
        doc, _ = completed_job
        resp = client.get(f"/api/v1/documents/{doc.id}/export?format=xml",
                          headers=auth_headers)
        assert resp.status_code == 422
