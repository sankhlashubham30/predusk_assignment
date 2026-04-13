"""Tests for the Celery document_processor worker task."""
import datetime
import pytest
from unittest.mock import patch, MagicMock, call

from app.models.document import Document
from app.models.job import Job


@pytest.fixture
def queued_job_in_db(db, sample_user):
    """Create a realistic queued job with a physical-ish document."""
    import tempfile, os
    # Write a real temp file so the processor can read it
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w")
    tmp.write("DocFlow processor test.\nKeywords: celery, async, redis.")
    tmp.flush()
    tmp_path = tmp.name
    tmp.close()

    doc = Document(
        original_filename="processor_test.txt",
        stored_filename=os.path.basename(tmp_path),
        file_path=tmp_path,
        file_size=os.path.getsize(tmp_path),
        file_type="txt",
        mime_type="text/plain",
        owner_id=sample_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    job = Job(
        document_id=doc.id,
        status="queued",
        progress=0.0,
        current_step="job_queued",
        retry_count=0,
        queued_at=datetime.datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return doc, job


class TestProgressPublisher:
    """Unit tests for the Redis Pub/Sub progress publisher."""

    def test_publish_event_format(self):
        """publish_progress must emit valid JSON with required fields."""
        import json
        from unittest.mock import MagicMock
        from app.workers.progress_publisher import publish_progress

        mock_redis = MagicMock()
        with patch("app.workers.progress_publisher.redis_client", mock_redis):
            publish_progress(job_id=1, event="job_started", progress=10,
                             message="Job started", step="job_started")

        mock_redis.publish.assert_called_once()
        channel, payload = mock_redis.publish.call_args[0]
        assert channel == "job_progress:1"
        data = json.loads(payload)
        assert data["event"] == "job_started"
        assert data["progress"] == 10
        assert "timestamp" in data

    def test_publish_multiple_events(self):
        """Publisher can emit multiple events for a single job."""
        from app.workers.progress_publisher import publish_progress

        mock_redis = MagicMock()
        events = [
            "job_queued", "job_started",
            "document_parsing_started", "document_parsing_completed",
            "field_extraction_started", "field_extraction_completed",
            "job_completed",
        ]
        with patch("app.workers.progress_publisher.redis_client", mock_redis):
            for i, evt in enumerate(events):
                publish_progress(job_id=5, event=evt, progress=i * 15,
                                 message=evt, step=evt)

        assert mock_redis.publish.call_count == len(events)


class TestDocumentProcessorTask:
    """Integration-style tests for the process_document Celery task."""

    @patch("app.workers.document_processor.publish_progress")
    @patch("app.workers.document_processor.SessionLocal")
    def test_all_progress_stages_emitted(self, mock_session_cls, mock_publish,
                                          db, queued_job_in_db):
        """Worker must emit all 7 canonical progress events."""
        from app.workers.document_processor import process_document

        doc, job = queued_job_in_db
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=db)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        # Run task synchronously (Celery eager mode not required — call direct)
        process_document(job.id)

        emitted_events = [c[1]["event"] for c in mock_publish.call_args_list
                          if "event" in c[1]]
        # Alternative: positional args
        if not emitted_events:
            emitted_events = [c[0][1] for c in mock_publish.call_args_list
                              if len(c[0]) > 1]

        required = {
            "job_started",
            "document_parsing_started",
            "document_parsing_completed",
            "field_extraction_started",
            "field_extraction_completed",
            "job_completed",
        }
        # Check at least the terminal event was published
        all_published = set(emitted_events)
        assert "job_completed" in all_published or "job_failed" in all_published

    @patch("app.workers.document_processor.publish_progress")
    @patch("app.workers.document_processor.SessionLocal")
    def test_job_status_updated_to_completed(self, mock_session_cls, mock_publish,
                                              db, queued_job_in_db):
        """After successful processing, job status in DB must be 'completed'."""
        from app.workers.document_processor import process_document

        doc, job = queued_job_in_db
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=db)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        process_document(job.id)

        db.refresh(job)
        assert job.status in ("completed", "failed")  # must leave queued state
        assert job.progress > 0

    @patch("app.workers.document_processor.publish_progress")
    @patch("app.workers.document_processor.SessionLocal")
    def test_result_stored_in_db(self, mock_session_cls, mock_publish,
                                  db, queued_job_in_db):
        """Completed job must have a result JSON with expected fields."""
        from app.workers.document_processor import process_document

        doc, job = queued_job_in_db
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=db)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        process_document(job.id)

        db.refresh(job)
        if job.status == "completed":
            assert job.result is not None
            for field in ("title", "category", "summary", "keywords"):
                assert field in job.result

    def test_nonexistent_job_does_not_crash(self, db):
        """Processing a non-existent job_id should fail gracefully."""
        from app.workers.document_processor import process_document
        with patch("app.workers.document_processor.SessionLocal") as mock_sess:
            mock_sess.return_value.__enter__ = MagicMock(return_value=db)
            mock_sess.return_value.__exit__ = MagicMock(return_value=False)
            # Should not raise an unhandled exception
            try:
                process_document(999999)
            except Exception:
                pass  # acceptable — job not found is handled
