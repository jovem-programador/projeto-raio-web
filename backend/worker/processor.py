import shutil, tempfile, subprocess
import pandas as pd
from pathlib import Path
from core.core_extracao import (
    preparar_pasta_temp,
    extrair_dados_completos_de_pasta_dxf,
    dataframe_to_excel_bytes,
)
from core.scriptTela import CAMPOS_ORDEM
from core.pdf_extracao import extrair_dados_completos_de_pasta_pdf


COLUNAS_MODELO_EXTRACAO = [
    *CAMPOS_ORDEM,
    "Nome_Arquivo",
    "_LAYOUT_ESCOLHIDO",
]


def _normalizar_para_modelo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Garante o padrão do arquivo 'Extração Raio.xlsx':
    - mesmas colunas
    - mesma ordem
    - colunas ausentes preenchidas com vazio
    """
    for col in COLUNAS_MODELO_EXTRACAO:
        if col not in df.columns:
            df[col] = ""

    return df[COLUNAS_MODELO_EXTRACAO].fillna("")

def processar_job(job_id, file_paths, result_dir, oda_path, redis_client):
    with tempfile.TemporaryDirectory() as tmp:
        tmp      = Path(tmp)
        dwg_dir  = tmp / "dwg"
        dxf_dir  = tmp / "dxf"
        pdf_dir  = tmp / "pdf"
        dwg_dir.mkdir()
        pdf_dir.mkdir()
        preparar_pasta_temp(dxf_dir)

        dwg_files = [p for p in file_paths if p.suffix.lower() == ".dwg"]
        pdf_files = [p for p in file_paths if p.suffix.lower() == ".pdf"]
        dados = []

        if dwg_files:
            # Copia DWGs para pasta temporária
            for p in dwg_files:
                shutil.copy(p, dwg_dir / p.name)

            # Converte via ODA
            cmd = [oda_path, str(dwg_dir), str(dxf_dir), "ACAD2018", "DXF", "0", "1"]
            subprocess.run(cmd, check=True, shell=True, timeout=300)

            # Extrai carimbos de DWG convertido
            dados.extend(extrair_dados_completos_de_pasta_dxf(dxf_dir, x_tol=420, y_tol=6))

        if pdf_files:
            # Copia PDFs para pasta temporária
            for p in pdf_files:
                shutil.copy(p, pdf_dir / p.name)

            # Extrai carimbos diretamente dos PDFs
            dados.extend(extrair_dados_completos_de_pasta_pdf(pdf_dir))
        
        if not dados:
            raise ValueError("Nenhum dado extraído dos arquivos enviados")

        # Atualiza progresso final no Redis
        redis_client.hset(f"job:{job_id}", "processed", len(file_paths))

        # Gera Excel
        df = pd.DataFrame(dados)
        df = _normalizar_para_modelo(df)
        excel_bytes = dataframe_to_excel_bytes(df)

        # Define o caminho final e guarda o ficheiro
        output_path = result_dir / f"{job_id}.xlsx"
        with open(output_path, "wb") as f:
            f.write(excel_bytes)

        # RETORNO CRÍTICO PARA O WORKER
        return output_path
