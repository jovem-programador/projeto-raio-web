from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("raio", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.task_serializer    = "json"
celery_app.conf.result_serializer  = "json"
celery_app.conf.accept_content     = ["json"]

@celery_app.task(bind=True, max_retries=2)
def processar_dwg(self, job_id: str, file_paths: list, result_dir: str, oda_path: str):
    import redis, traceback
    from pathlib import Path
    from worker.processor import processar_job

    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.hset(f"job:{job_id}", "status", "processing")

    try:
        result_path = processar_job(
            job_id=job_id,
            file_paths=[Path(p) for p in file_paths],
            result_dir=Path(result_dir),
            oda_path=oda_path,
            redis_client=r,
        )
        r.hset(f"job:{job_id}", mapping={
            "status": "done",
            "result_path": str(result_path),
        })
    except Exception as exc:
        r.hset(f"job:{job_id}", mapping={
            "status": "error",
            "error_msg": str(exc),
        })
        raise self.retry(exc=exc, countdown=5)