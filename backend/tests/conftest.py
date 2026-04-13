"""Pytest fixtures shared across all test modules."""
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock, patch

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.models.document import Document
from app.models.job import Job

# ── In-memory SQLite for tests ────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """FastAPI test client with overridden DB session."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user(db):
    """Create a test user in the database."""
    from app.core.security import hash_password
    user = User(
        email="test@docflow.dev",
        username="testuser",
        hashed_password=hash_password("TestPass123!"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, sample_user):
    """Return Authorization headers for the test user."""
    resp = client.post("/api/v1/auth/login", data={
        "username": sample_user.email,
        "password": "TestPass123!",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_txt_file():
    """Return an in-memory text file upload."""
    content = b"DocFlow test document.\nThis is sample content for unit testing."
    return ("files", ("test.txt", io.BytesIO(content), "text/plain"))


@pytest.fixture
def completed_job(db, sample_user):
    """Pre-seeded completed document + job pair."""
    import json, datetime
    doc = Document(
        original_filename="sample.txt",
        stored_filename="sample_stored.txt",
        file_path="/tmp/sample_stored.txt",
        file_size=128,
        file_type="txt",
        mime_type="text/plain",
        owner_id=sample_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    result = {
        "title": "Sample Document",
        "category": "test",
        "summary": "A test document.",
        "keywords": ["test", "docflow"],
        "confidence_score": 0.92,
        "metadata": {"word_count": 10},
    }
    job = Job(
        document_id=doc.id,
        status="completed",
        progress=100.0,
        current_step="job_completed",
        result=result,
        is_reviewed=False,
        is_finalized=False,
        retry_count=0,
        queued_at=datetime.datetime.utcnow(),
        started_at=datetime.datetime.utcnow(),
        completed_at=datetime.datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return doc, job
