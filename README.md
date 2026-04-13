# DocFlow — Async Document Processing Workflow System

> **Full Stack Assignment** · FastAPI · Celery · Redis · PostgreSQL · Next.js 14

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org)
[![Redis](https://img.shields.io/badge/Redis-7-red)](https://redis.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue)](https://docker.com)

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Setup Instructions](#setup-instructions)
- [Run Steps](#run-steps)
- [API Reference](#api-reference)
- [Feature Checklist](#feature-checklist)
- [Assumptions](#assumptions)
- [Tradeoffs](#tradeoffs)
- [Limitations](#limitations)
- [AI Tools Disclosure](#ai-tools-disclosure)

---

## Overview

DocFlow is a production-style full stack application for asynchronous document processing. Users upload documents, background Celery workers process them through a multi-stage pipeline, Redis Pub/Sub streams live progress to the frontend via Server-Sent Events, and users can review, edit, finalize, and export extracted results.

**The system is evaluated on architecture quality, not AI/OCR sophistication.** Processing logic is intentionally simple (metadata extraction + structured field generation) while the async infrastructure is production-grade.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│          Next.js 14 · TypeScript · TailwindCSS                   │
│   Upload → Dashboard → Detail/Review → Finalize → Export         │
└────────────────────────┬─────────────────────────────────────────┘
                         │ HTTP / SSE
┌────────────────────────▼─────────────────────────────────────────┐
│                         API LAYER                                │
│                  FastAPI (Python 3.11)                           │
│  /upload  /list  /detail  /progress(SSE)  /retry  /export       │
│       JWT Auth · Pydantic DTOs · Service Layer                   │
└────────┬──────────────────────────────────┬────────────────────--┘
         │ SQLAlchemy ORM                   │ Celery task dispatch
┌────────▼───────────┐            ┌─────────▼──────────────────────┐
│   PostgreSQL 15    │            │      Redis 7                   │
│  Documents + Jobs  │            │  Celery Broker + Pub/Sub       │
│  Users + Results   │            │  channel: job_progress:{id}    │
└────────────────────┘            └─────────┬──────────────────────┘
                                            │
                               ┌────────────▼────────────┐
                               │    Celery Worker        │
                               │  document_processor.py  │
                               │                         │
                               │  1. job_queued          │
                               │  2. job_started         │
                               │  3. parsing_started     │
                               │  4. parsing_completed   │
                               │  5. extraction_started  │
                               │  6. extraction_done     │
                               │  7. job_completed       │
                               └─────────────────────────┘
```

### Key Design Decisions

| Concern | Decision | Rationale |
|---|---|---|
| Progress delivery | Server-Sent Events (SSE) | Simpler than WebSocket for unidirectional server→client streaming; works over HTTP/1.1 |
| Task queue | Celery + Redis broker | Industry standard; natural Redis Pub/Sub integration |
| Progress channel | `job_progress:{job_id}` | Per-job isolation; SSE endpoint subscribes only to the relevant channel |
| Storage abstraction | `BaseStorage` interface | `LocalFileStorage` today; swap to `S3Storage` without changing service code |
| Auth | Optional JWT | Upload and listing work without auth; auth headers unlock ownership scoping |
| DB migrations | Alembic | Schema version control from day one |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 + TypeScript + Tailwind CSS |
| Backend | FastAPI (Python 3.11) |
| Database | PostgreSQL 15 (SQLAlchemy + Alembic) |
| Task Queue | Celery 5.x |
| Message Broker | Redis 7 (broker + Pub/Sub) |
| Progress Streaming | Redis Pub/Sub → FastAPI SSE |
| Auth | JWT (python-jose + passlib) |
| Containerisation | Docker + Docker Compose |
| Testing | pytest + pytest-cov |

---

## Setup Instructions

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (recommended)
- OR: Python 3.11+, Node.js 20+, PostgreSQL 15, Redis 7

### Environment Variables

Copy the example file and fill in values:

```bash
cp .env.example .env
```

Key variables:

```env
# Database
DATABASE_URL=postgresql://docflow:docflow@localhost:5432/docflow

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS — set to your frontend URL
CORS_ORIGINS=["http://localhost:3000"]
```

---

## Run Steps

### Option A — Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/Aditya-Singh-031/docflow.git
cd docflow

# Copy environment file
cp .env.example .env

# Start all services (PostgreSQL, Redis, API, Worker, Frontend)
docker compose up --build

# The app will be available at:
#   Frontend:  http://localhost:3000
#   API:       http://localhost:8000
#   API Docs:  http://localhost:8000/docs
```

### Option B — Local Development

**1. Start PostgreSQL and Redis** (Docker for just the infra):

```bash
docker compose -f docker-compose.dev.yml up -d
```

**2. Backend setup:**

```bash
cd backend
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

**3. Start Celery worker** (new terminal):

```bash
cd backend
source venv/Scripts/activate
celery -A app.workers.celery_app worker --loglevel=info -P solo
```

> **Windows note:** Use `-P solo` for the Celery worker on Windows (avoids multiprocessing issues).

**4. Frontend setup** (new terminal):

```bash
cd frontend
npm install
npm run dev
```

App is now live at **http://localhost:3000**.

### Running Tests

```bash
cd backend
source venv/Scripts/activate
pip install -r requirements-test.txt
pytest

# With coverage report
pytest --cov=app --cov-report=term-missing
```

---

## API Reference

Full interactive docs: **http://localhost:8000/docs**

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | — | Register new user |
| `POST` | `/api/v1/auth/login` | — | Get JWT access token |
| `GET` | `/api/v1/auth/me` | ✓ | Get current user profile |
| `POST` | `/api/v1/documents/upload` | Optional | Upload 1+ documents |
| `GET` | `/api/v1/documents/` | Optional | List jobs (search, filter, sort, paginate) |
| `GET` | `/api/v1/documents/{id}` | Optional | Get document + job details |
| `GET` | `/api/v1/documents/{id}/progress` | — | SSE stream — live progress events |
| `PUT` | `/api/v1/documents/{id}/result` | Optional | Update reviewed result |
| `POST` | `/api/v1/documents/{id}/finalize` | Optional | Lock and finalize result |
| `POST` | `/api/v1/documents/{id}/retry` | Optional | Retry a failed job |
| `GET` | `/api/v1/documents/{id}/export?format=json` | Optional | Export as JSON |
| `GET` | `/api/v1/documents/{id}/export?format=csv` | Optional | Export as CSV |
| `GET` | `/api/v1/health` | — | Health check |

### Progress Events (SSE)

Subscribe to `GET /api/v1/documents/{id}/progress` for a stream of JSON events:

```json
{ "event": "job_started",               "progress": 10, "message": "Worker picked up job",    "timestamp": "..." }
{ "event": "document_parsing_started",  "progress": 20, "message": "Parsing document",        "timestamp": "..." }
{ "event": "document_parsing_completed","progress": 50, "message": "Parsing complete",        "timestamp": "..." }
{ "event": "field_extraction_started",  "progress": 60, "message": "Extracting fields",       "timestamp": "..." }
{ "event": "field_extraction_completed","progress": 90, "message": "Extraction complete",     "timestamp": "..." }
{ "event": "job_completed",             "progress": 100,"message": "Processing complete",    "timestamp": "..." }
```

---

## Feature Checklist

### Mandatory Features

- [x] Upload one or more documents
- [x] Save document metadata and job details in PostgreSQL
- [x] Create background processing job using **Celery**
- [x] Use **Redis Pub/Sub** to publish progress events from worker
- [x] Display job states: Queued → Processing → Completed / Failed
- [x] Show live progress in frontend via **Server-Sent Events**
- [x] Document list/dashboard with **search**, **filter by status**, **sorting**
- [x] Document detail page — review and edit extracted output
- [x] Allow finalization of reviewed output
- [x] Support **retry** for failed jobs
- [x] Export finalized records as **JSON** and **CSV**

### Bonus Features

- [x] **Docker Compose** setup — full one-command startup
- [x] **Pytest tests** — API, service layer, and worker tests
- [x] **JWT Authentication** — register, login, token-scoped access
- [x] **Idempotent retry** — Celery task ID tracked; retry resets job state safely
- [x] **Cancellation support** — active jobs can be revoked via Celery
- [x] **File storage abstraction** — `BaseStorage` interface with `LocalFileStorage`; S3-ready
- [x] **Clean deployment-ready structure** — layered architecture (API → Service → Worker)
- [x] **Large file / edge case handling** — file size limits, type validation, error states

---

## Assumptions

1. **Processing logic is simulated** — The worker extracts real metadata (filename, size, word count) and generates structured fields. It does not use an external AI/OCR API. Per the problem statement: *"You are not being evaluated on advanced AI or OCR quality."*

2. **Authentication is optional** — Endpoints accept both authenticated and anonymous requests. Authenticated users see only their own documents; anonymous uploads are stored without an owner.

3. **File storage is local** — Files are stored on disk at `UPLOAD_DIR` (default: `./uploads`). The storage interface is abstracted for easy S3 swap.

4. **SSE for progress** — Server-Sent Events chosen over WebSockets (simpler, HTTP/1.1 compatible, sufficient for unidirectional server→client progress streaming).

5. **Single Celery worker** — The default `docker-compose.yml` starts one worker. Scale with `docker compose up --scale worker=N`.

---

## Tradeoffs

| Decision | Tradeoff Made | Alternative Considered |
|---|---|---|
| SSE over WebSocket | Simpler protocol, one-way only | WebSocket supports bidirectional but adds complexity |
| SQLite for tests | Zero infrastructure needed for CI | Could use testcontainers for PostgreSQL parity |
| Optional auth | Lower barrier to demo/test | Mandatory auth would require token setup in all test flows |
| Local file storage | Simple setup, no cloud deps | S3/MinIO would be production-ideal but adds setup friction |
| Simulated NLP | No API keys needed | Real LLM calls would require API keys and add latency/cost |
| `-P solo` on Windows | Celery works on Windows without extra setup | `prefork` pool is faster but broken on Windows without WSL |

---

## Limitations

1. **No WebSocket** — SSE is unidirectional. Clients cannot send mid-stream control messages (e.g., pause).
2. **Local storage only** — Uploaded files are stored on the host; not replicated across containers by default.
3. **Single DB** — No read replicas. High-concurrency reads may bottleneck under heavy load.
4. **No rate limiting** — Upload endpoint has no per-IP rate limiting (would add `slowapi` in production).
5. **SQLite in tests** — Test suite runs on SQLite, not PostgreSQL. JSON column behavior may differ slightly.
6. **No email verification** — User registration does not send a confirmation email.

---

## AI Tools Disclosure

This project was developed **with assistance from AI coding tools**, specifically:

- **Perplexity AI** — used for architectural guidance, code review, and scaffolding suggestions
- **GitHub Copilot** — used for inline code completion

All code was reviewed, understood, and verified by the developer. The system architecture, design decisions, and integration logic are the developer's own work. AI tools were used as an accelerator, not a replacement for engineering judgment.

---

## Project Structure

```
docflow/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route handlers (thin layer)
│   │   ├── core/            # Config, security, dependencies
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic DTOs
│   │   ├── services/        # Business logic
│   │   ├── storage/         # File storage abstraction
│   │   ├── workers/         # Celery tasks + Redis publisher
│   │   └── db/              # Session + Base
│   ├── alembic/             # DB migrations
│   └── tests/               # pytest test suite
├── frontend/
│   └── src/
│       ├── app/             # Next.js App Router pages
│       ├── components/      # UI component library
│       ├── hooks/           # Custom React hooks
│       ├── lib/             # API client + utils
│       └── types/           # TypeScript interfaces
├── sample_files/            # Test documents + sample exports
├── docker-compose.yml       # Production-ready compose
├── docker-compose.dev.yml   # Dev infrastructure only
└── .env.example
```

---

*Built for the DocFlow Full Stack Assignment · April 2026*
