from celery import Celery
import os
import redis
import traceback
from datetime import datetime, timezone
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

    # Se o usuário limpou o histórico antes do worker iniciar, não recria o job no Redis.
    if r.get(f"job_deleted:{job_id}") == "1":
        return f"Job {job_id} ignorado (removido pelo usuário)."

    r.hset(
        f"job:{job_id}",
        mapping={
            "status": "processing",
            "started_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    try:
        # Reconstroi os caminhos baseados no job_id
        job_upload_dir = UPLOAD_DIR / job_id
        # Lista os ficheiros suportados dentro da pasta do job
        file_paths = [
            p for p in job_upload_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".dwg", ".pdf", ".docx"}
        ]

        if not file_paths:
            raise Exception(f"Nenhum ficheiro suportado (.dwg/.pdf/.docx) encontrado na pasta {job_upload_dir}")

        job_data = r.hgetall(f"job:{job_id}")
        finished_at = datetime.now(timezone.utc).isoformat()
        raw_filenames = job_data.get("filenames", "")
        metadata = {
            "job_id": job_id,
            "user": job_data.get("user", ""),
            "created_at": job_data.get("created_at", ""),
            "finished_at": finished_at,
            "total_files": job_data.get("total_files", len(file_paths)),
            "filenames": raw_filenames.split(",") if raw_filenames else [p.name for p in file_paths],
            "version": "Projeto Raio 1.0.0",
        }

        # Chama o processador
        result_path = processar_job(
            job_id=job_id,
            file_paths=file_paths,
            result_dir=RESULT_DIR,
            oda_path=ODA_PATH,
            redis_client=r,
            metadata=metadata,
        )

        # Se foi removido durante o processamento, não regrava status final.
        if r.get(f"job_deleted:{job_id}") == "1":
            return f"Job {job_id} concluído, mas ocultado por limpeza de histórico."

        r.hset(f"job:{job_id}", mapping={
            "status": "done",
            "result_path": str(result_path),
            "finished_at": finished_at,
        })
        
        return f"Job {job_id} concluído com sucesso."

    except Exception as e:
        error_details = traceback.format_exc()

        # Se removido, não restaura item com status de erro.
        if r.get(f"job_deleted:{job_id}") == "1":
            return f"Job {job_id} falhou após remoção do histórico."

        r.hset(f"job:{job_id}", mapping={
            "status": "error",
            "error_msg": str(e),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })
        print(f"Erro no Job {job_id}:\n{error_details}")
        return f"Erro no Job {job_id}"
