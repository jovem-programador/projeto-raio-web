"""
Developer: Anderson Marley
GitHub: jovem-programador
Date: 02/03/2026
"""

import os
import subprocess
import shutil
from pathlib import Path
import io
import pandas as pd
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

# importe aqui suas funções existentes:
# - extract_all_texts, fill_by_alias_tags, fill_by_key_value_text, etc.
# - extrair_carimbo_de_um_dxf (mas vamos permitir x_tol/y_tol)

from core.scriptTela import extrair_carimbo_de_um_dxf  # você vai mover seu código para cá

def preparar_pasta_temp(pasta: Path):
    if pasta.exists():
        shutil.rmtree(pasta)
    pasta.mkdir(parents=True, exist_ok=True)

def converter_dwg_para_dxf_oda(path_oda: str, pasta_dwg_origem: Path, pasta_dxf_destino: Path, dxf_version: str):
    if not Path(path_oda).exists():
        raise FileNotFoundError(f"ODA Converter não localizado em: {path_oda}")

    comando = [path_oda, str(pasta_dwg_origem), str(pasta_dxf_destino), dxf_version, "DXF", "0", "1"]
    # shell=True no Windows pode ser necessário em alguns ambientes; mantenha se você já usa assim
    subprocess.run(comando, check=True, shell=True)

def extrair_dados_completos_de_pasta_dxf(pasta_dxf: Path, x_tol: float, y_tol: float):
    resultados = []
    arquivos = sorted([p for p in pasta_dxf.glob("*.dxf")])

    for dxf_path in arquivos:
        carimbo = extrair_carimbo_de_um_dxf(str(dxf_path), x_tol=x_tol, y_tol=y_tol)  # aqui você pode passar x_tol/y_tol se adaptar a assinatura
        if carimbo:
            resultados.append(carimbo)

    return resultados

def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        sheet = "Extracao"
        df.to_excel(writer, index=False, sheet_name=sheet)

        # pega workbook/worksheet do writer
        wb = writer.book
        ws = wb[sheet]

        # intervalo usado (A1 até última coluna/linha)
        max_row = ws.max_row
        max_col = ws.max_column
        last_col = get_column_letter(max_col)
        table_range = f"A1:{last_col}{max_row}"

        # nome da tabela (sem espaço/acentos)
        tab = Table(displayName="TabelaRaio", ref=table_range)

        style = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        tab.tableStyleInfo = style

        ws.add_table(tab)

        # (opcional) congelar cabeçalho
        ws.freeze_panes = "A2"

    output.seek(0)
    return output.getvalue()