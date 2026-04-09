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

        # Copia DWGs para pasta temporária
        for p in file_paths:
            shutil.copy(p, dwg_dir / p.name)

        # Converte via ODA
        cmd = [oda_path, str(dwg_dir), str(dxf_dir), "ACAD2018", "DXF", "0", "1"]
        subprocess.run(cmd, check=True, shell=True, timeout=300)

        # Extrai carimbos
        dados = extrair_dados_completos_de_pasta_dxf(dxf_dir, x_tol=420, y_tol=6)
        
        if not dados:
            raise ValueError("Nenhum dado extraído dos arquivos enviados")

        # Atualiza progresso final no Redis
        redis_client.hset(f"job:{job_id}", "processed", len(file_paths))

        # Gera Excel
        df = pd.DataFrame(dados)
        excel_bytes = dataframe_to_excel_bytes(df)

        # Define o caminho final e guarda o ficheiro
        output_path = result_dir / f"{job_id}.xlsx"
        with open(output_path, "wb") as f:
            f.write(excel_bytes)

        # RETORNO CRÍTICO PARA O WORKER
        return output_path