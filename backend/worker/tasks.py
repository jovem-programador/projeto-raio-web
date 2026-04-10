from celery import Celery
import os
import redis
import traceback
from pathlib import Path

# Configurações de ambiente (devem ser as mesmas do main.py)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "storage/uploads"))
RESULT_DIR = Path(os.getenv("RESULT_DIR", "storage/results"))
# Caminho do ODA Converter (ajuste se necessário)
ODA_PATH = os.getenv("ODA_PATH", r"C:\Program Files\ODA\ODAFileConverter 26.12.0\ODAFileConverter.exe")

celery_app = Celery("raio", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.task_serializer    = "json"
celery_app.conf.result_serializer  = "json"
celery_app.conf.accept_content     = ["json"]

@celery_app.task(bind=True, max_retries=0)
def processar_dwg(self, job_id: str):
    from worker.processor import processar_job

    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.hset(f"job:{job_id}", "status", "processing")

    try:
        # Reconstroi os caminhos baseados no job_id
        job_upload_dir = UPLOAD_DIR / job_id
        # Lista todos os ficheiros .dwg dentro da pasta do job
        file_paths = [Path(f) for f in job_upload_dir.glob("*.dwg")]

        if not file_paths:
            raise Exception(f"Nenhum ficheiro .dwg encontrado na pasta {job_upload_dir}")

        # Chama o processador
        result_path = processar_job(
            job_id=job_id,
            file_paths=file_paths,
            result_dir=RESULT_DIR,
            oda_path=ODA_PATH,
            redis_client=r,
        )

        r.hset(f"job:{job_id}", mapping={
            "status": "done",
            "result_path": str(result_path),
        })
        
        return f"Job {job_id} concluído com sucesso."

    except Exception as e:
        error_details = traceback.format_exc()
        r.hset(f"job:{job_id}", mapping={
            "status": "error",
            "error_msg": str(e)
        })
        print(f"Erro no Job {job_id}:\n{error_details}")
        return f"Erro no Job {job_id}"