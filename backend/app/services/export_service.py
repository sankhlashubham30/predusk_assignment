import csv
import json
import io
from app.models.job import Job


def export_as_json(job: Job) -> str:
    """Return finalized result as formatted JSON string."""
    data = job.reviewed_result if job.reviewed_result else job.result
    return json.dumps({
        "job_id": job.id,
        "document_id": job.document_id,
        "status": job.status,
        "is_finalized": job.is_finalized,
        "result": data,
        "exported_at": __import__("datetime").datetime.utcnow().isoformat(),
    }, indent=2, default=str)


def export_as_csv(job: Job) -> str:
    """Flatten result fields into CSV format."""
    data = job.reviewed_result if job.reviewed_result else job.result or {}
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["field", "value"])
    writer.writerow(["job_id", job.id])
    writer.writerow(["document_id", job.document_id])
    writer.writerow(["status", job.status])
    writer.writerow(["is_finalized", job.is_finalized])

    for key, value in data.items():
        if isinstance(value, (dict, list)):
            writer.writerow([key, json.dumps(value)])
        else:
            writer.writerow([key, value])

    return output.getvalue()
