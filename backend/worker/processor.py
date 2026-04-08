import shutil, tempfile, subprocess
import pandas as pd
from pathlib import Path
from core.core_extracao import (
    preparar_pasta_temp,
    extrair_dados_completos_de_pasta_dxf,
    dataframe_to_excel_bytes,
)

def processar_job(job_id, file_paths, result_dir, oda_path, redis_client):
    with tempfile.TemporaryDirectory() as tmp:
        tmp      = Path(tmp)
        dwg_dir  = tmp / "dwg"
        dxf_dir  = tmp / "dxf"
        dwg_dir.mkdir(); preparar_pasta_temp(dxf_dir)

        # copia DWGs para pasta temporária
        for p in file_paths:
            shutil.copy(p, dwg_dir / p.name)

        # converte via ODA
        cmd = [oda_path, str(dwg_dir), str(dxf_dir), "ACAD2018", "DXF", "0", "1"]
        subprocess.run(cmd, check=True, shell=True, timeout=300)

        redis_client.hset(f"job:{job_id}", "processed", len(file_paths) // 2)

        # extrai carimbos
        dados = extrair_dados_completos_de_pasta_dxf(dxf_dir, x_tol=420, y_tol=6)
        if not dados:
            raise ValueError("Nenhum dado extraído dos arquivos enviados")

        redis_client.hset(f"job:{job_id}", "processed", len(file_paths))

        # gera Excel
        df          = pd.DataFrame(dados)
        excel_bytes = dataframe_to_excel_bytes(df)

        result_dir.mkdir(parents=True, exist_ok=True)
        result_path = result_dir / f"{job_id}.xlsx"
        result_path.write_bytes(excel_bytes)

    return result_path