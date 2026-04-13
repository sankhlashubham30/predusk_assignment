import json
import asyncio
import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.job import Job

router = APIRouter()


async def event_stream(job_id: int):
    """
    Async generator that:
    1. Sends current job state immediately (for late-joiners)
    2. Subscribes to Redis Pub/Sub channel for live events
    3. Yields SSE-formatted messages
    4. Falls back to polling if no event in 15s (heartbeat)
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
            return

        # Send current state immediately
        initial = {
            "job_id": job_id,
            "event": "current_state",
            "progress": job.progress,
            "message": f"Current status: {job.status}",
            "data": {"status": job.status, "current_step": job.current_step},
        }
        yield f"data: {json.dumps(initial)}\n\n"

        if job.status in ("completed", "failed", "cancelled"):
            return
    finally:
        db.close()

    # Subscribe to Redis Pub/Sub
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    channel = f"job_progress:{job_id}"
    await pubsub.subscribe(channel)

    try:
        timeout_counter = 0
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

            if message and message["type"] == "message":
                timeout_counter = 0
                data = message["data"]
                yield f"data: {data}\n\n"

                parsed = json.loads(data)
                if parsed.get("event") in ("job_completed", "job_failed"):
                    break
            else:
                timeout_counter += 1
                if timeout_counter % 15 == 0:
                    # Heartbeat every 15s to keep connection alive
                    yield f": heartbeat\n\n"
                if timeout_counter > 300:  # 5 minute max
                    break
                await asyncio.sleep(0)
    finally:
        await pubsub.unsubscribe(channel)
        await r.aclose()


@router.get("/{job_id}/stream")
async def stream_job_progress(job_id: int):
    """Server-Sent Events endpoint for real-time job progress."""
    return StreamingResponse(
        event_stream(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/{job_id}/status")
def get_job_status(job_id: int):
    """Polling fallback — returns latest cached status from Redis."""
    import redis as sync_redis
    r = sync_redis.from_url(settings.REDIS_URL, decode_responses=True)
    cached = r.get(f"job_status:{job_id}")
    if cached:
        return json.loads(cached)

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {
            "job_id": job_id,
            "event": "current_state",
            "progress": job.progress,
            "message": job.current_step or job.status,
            "data": {"status": job.status},
        }
    finally:
        db.close()