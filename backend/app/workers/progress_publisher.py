import json
import redis
from datetime import datetime, timezone
from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def publish_progress(
    job_id: int,
    event: str,
    progress: float,
    message: str,
    data: dict = None
):
    """Publish a progress event to Redis Pub/Sub channel for a job."""
    payload = {
        "job_id": job_id,
        "event": event,
        "progress": progress,
        "message": message,
        "data": data or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    channel = f"job_progress:{job_id}"
    redis_client.publish(channel, json.dumps(payload))

    # Also store latest status in Redis key (for polling fallback)
    redis_client.setex(
        f"job_status:{job_id}",
        300,  # TTL 5 minutes
        json.dumps(payload)
    )