import json
from collections.abc import Callable

from sqlalchemy.orm import Session

from backend_v2.database import SessionLocal
from backend_v2.models import Job


JobHandler = Callable[[Session, Job], dict]


def update_job(db: Session, job: Job, percent: int, message: str) -> None:
    job.status = "RUNNING"
    job.progress_percent = max(0, min(100, percent))
    job.progress_message = message
    db.commit()


def run_job(job_id: str, handler: JobHandler) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if not job:
            return
        update_job(db, job, 5, "Pekerjaan dimulai")
        result = handler(db, job)
        job.status = "SUCCEEDED"
        job.progress_percent = 100
        job.progress_message = "Selesai"
        job.result_json = json.dumps(result, ensure_ascii=False)
        db.commit()
    except Exception as exc:  # pragma: no cover - exercised through API integration
        job = db.get(Job, job_id)
        if job:
            job.status = "FAILED"
            job.progress_message = "Proses gagal"
            job.error_message = str(exc)
            db.commit()
    finally:
        db.close()
