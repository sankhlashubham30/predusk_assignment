"""Tests for the document service layer."""
import io
import pytest
from unittest.mock import MagicMock, patch
from fastapi import UploadFile

from app.services.document_service import create_document_and_job, get_all_jobs
from app.models.document import Document
from app.models.job import Job


class TestCreateDocumentAndJob:
    @patch("app.services.document_service.process_document")
    @patch("app.services.document_service.storage")
    def test_creates_document_record(self, mock_storage, mock_task, db, sample_user):
        """Uploading a file creates a Document row in the database."""
        mock_storage.save.return_value = ("/tmp/stored.txt", "stored_abc.txt")
        mock_task.delay.return_value = MagicMock(id="task-111")

        upload = UploadFile(
            filename="hello.txt",
            file=io.BytesIO(b"Hello world"),
        )
        doc, job = create_document_and_job(db, upload, owner_id=sample_user.id)

        assert doc.id is not None
        assert doc.original_filename == "hello.txt"
        assert doc.file_type == "txt"
        assert doc.owner_id == sample_user.id

    @patch("app.services.document_service.process_document")
    @patch("app.services.document_service.storage")
    def test_creates_job_record(self, mock_storage, mock_task, db, sample_user):
        """Uploading a file creates a corresponding Job row."""
        mock_storage.save.return_value = ("/tmp/stored.txt", "stored_abc.txt")
        mock_task.delay.return_value = MagicMock(id="task-222")

        upload = UploadFile(filename="doc.txt", file=io.BytesIO(b"content"))
        doc, job = create_document_and_job(db, upload, owner_id=sample_user.id)

        assert job.id is not None
        assert job.document_id == doc.id
        assert job.status == "queued"
        assert job.celery_task_id == "task-222"

    @patch("app.services.document_service.process_document")
    @patch("app.services.document_service.storage")
    def test_celery_task_dispatched(self, mock_storage, mock_task, db):
        """Celery task is called with the correct job_id."""
        mock_storage.save.return_value = ("/tmp/stored.txt", "stored.txt")
        mock_task.delay.return_value = MagicMock(id="task-dispatch")

        upload = UploadFile(filename="dispatch.txt", file=io.BytesIO(b"data"))
        doc, job = create_document_and_job(db, upload, owner_id=None)

        mock_task.delay.assert_called_once_with(job.id)


class TestGetAllJobs:
    @patch("app.services.document_service.process_document")
    @patch("app.services.document_service.storage")
    def test_get_all_jobs_returns_items(self, mock_storage, mock_task, db, sample_user):
        mock_storage.save.return_value = ("/tmp/x.txt", "x.txt")
        mock_task.delay.return_value = MagicMock(id="t")

        upload = UploadFile(filename="listed.txt", file=io.BytesIO(b"list me"))
        create_document_and_job(db, upload, owner_id=sample_user.id)

        results, total = get_all_jobs(db, owner_id=sample_user.id)
        assert total >= 1
        assert len(results) >= 1

    @patch("app.services.document_service.process_document")
    @patch("app.services.document_service.storage")
    def test_filter_by_status(self, mock_storage, mock_task, db, sample_user):
        mock_storage.save.return_value = ("/tmp/y.txt", "y.txt")
        mock_task.delay.return_value = MagicMock(id="t2")

        upload = UploadFile(filename="filter.txt", file=io.BytesIO(b"filter"))
        create_document_and_job(db, upload, owner_id=sample_user.id)

        results, total = get_all_jobs(db, owner_id=sample_user.id, status_filter="queued")
        for job, doc in results:
            assert job.status == "queued"

    def test_empty_results(self, db):
        results, total = get_all_jobs(db, owner_id=99999)
        assert total == 0
        assert results == []
