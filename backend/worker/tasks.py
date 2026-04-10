from celery import Celery
import os
import redis
import traceback
from pathlib import Path

# Configurações de ambiente (devem ser as mesmas do main.py)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "storage/uploads"))
RESULT_DIR = Path(os.getenv("RESULT_DIR", "storage/results"))

# Caminho do ODA Converter
ODA_PATH = os.getenv("ODA_PATH", r"C:\Program Files\ODA\ODAFileConverter 26.12.0\ODAFileConverter.exe")

celery_app = Celery("raio", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.task_serializer    = "json"
celery_app.conf.result_serializer  = "json"
celery_app.conf.accept_content     = ["json"]

@celery_app.task(bind=True, max_retries=0)
def processar_dwg(self, job_id: str, job_path: str):
    # Importação tardia para evitar problemas de circularidade
    from worker.processor import processar_job

    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.hset(f"job:{job_id}", "status", "processing")

    try:
        # Usa o caminho enviado pelo main.py
        job_upload_dir = Path(job_path)
        
        # Lista os ficheiros .dwg
        file_paths = [Path(f) for f in job_upload_dir.glob("*.dwg")]

        if not file_paths:
            raise Exception(f"Nenhum ficheiro .dwg encontrado em {job_upload_dir}")

        # Executa o processamento real
        result_path = processar_job(
            job_id=job_id,
            file_paths=file_paths,
            result_dir=RESULT_DIR,
            oda_path=ODA_PATH,
            redis_client=r,
        )

        # --- O PONTO CHAVE: ATUALIZAR O REDIS PARA O FRONTEND ---
        r.hset(f"job:{job_id}", mapping={
            "status": "done",
            "processed": len(file_paths),
            "download_ready": "true"  # Deve ser string "true" para o Next.js reconhecer como booleano
        })

        return f"Job {job_id} concluído com sucesso."

    except Exception as e:
        print(f"Erro no processamento do job {job_id}: {str(e)}")
        traceback.print_exc()
        
        # Avisa o Redis sobre a falha
        r.hset(f"job:{job_id}", mapping={
            "status": "error",
            "error_msg": str(e),
            "download_ready": "false"
        })
        raise e