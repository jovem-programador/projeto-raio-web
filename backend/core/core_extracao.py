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
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
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

def _safe_sheet_value(value):
    if value is None:
        return ""
    return str(value)


def _local_timezone():
    timezone_name = os.getenv("APP_TIMEZONE", "America/Fortaleza")
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=-3), name="BRT")


def _format_datetime_for_sheet(value):
    if not value:
        return ""

    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value).strip()
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return raw

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(_local_timezone()).strftime("%d/%m/%Y %H:%M:%S")


def _add_autenticidade_sheet(writer, metadata: dict | None):
    meta = metadata or {}
    wb = writer.book
    ws = wb.create_sheet("Autenticidade", 0)

    red = "C80000"
    dark = "111827"
    gray = "6B7280"
    light_red = "FEE2E2"
    light_gray = "F9FAFB"
    border_color = "E5E7EB"

    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 26
    ws.column_dimensions["C"].width = 72
    ws.column_dimensions["D"].width = 4

    ws.merge_cells("B2:C2")
    ws["B2"] = "PROJETO RAIO"
    ws["B2"].font = Font(bold=True, size=22, color=red)
    ws["B2"].alignment = Alignment(horizontal="center")

    ws.merge_cells("B3:C3")
    ws["B3"] = "Extração autenticada"
    ws["B3"].font = Font(bold=True, size=14, color=dark)
    ws["B3"].alignment = Alignment(horizontal="center")

    ws.merge_cells("B5:C5")
    ws["B5"] = "Este arquivo foi gerado automaticamente pelo Projeto Raio a partir dos arquivos processados abaixo."
    ws["B5"].font = Font(size=11, color=gray)
    ws["B5"].alignment = Alignment(horizontal="center", wrap_text=True)

    thin = Side(style="thin", color=border_color)
    label_fill = PatternFill("solid", fgColor=light_red)
    value_fill = PatternFill("solid", fgColor=light_gray)

    fields = [
        ("ID do processamento", meta.get("job_id")),
        ("Usuário", meta.get("user")),
        ("Criado em", _format_datetime_for_sheet(meta.get("created_at"))),
        ("Finalizado em", _format_datetime_for_sheet(meta.get("finished_at"))),
        ("Versão do software", meta.get("version", "Projeto Raio 1.0.0")),
        ("Total de arquivos", meta.get("total_files")),
        ("Arquivos processados", ", ".join(meta.get("filenames", []))),
    ]

    row = 7
    for label, value in fields:
        ws.cell(row=row, column=2, value=label)
        ws.cell(row=row, column=3, value=_safe_sheet_value(value))

        for col in (2, 3):
            cell = ws.cell(row=row, column=col)
            cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
            cell.alignment = Alignment(vertical="top", wrap_text=True)

        ws.cell(row=row, column=2).font = Font(bold=True, color=dark)
        ws.cell(row=row, column=2).fill = label_fill
        ws.cell(row=row, column=3).fill = value_fill
        row += 1

    ws.merge_cells(start_row=row + 1, start_column=2, end_row=row + 1, end_column=3)
    ws.cell(row=row + 1, column=2, value="Selo de autenticidade")
    ws.cell(row=row + 1, column=2).font = Font(bold=True, size=12, color=red)
    ws.cell(row=row + 1, column=2).alignment = Alignment(horizontal="center")

    ws.merge_cells(start_row=row + 2, start_column=2, end_row=row + 4, end_column=3)
    seal = ws.cell(row=row + 2, column=2)
    seal.value = f"PROJETO RAIO\nEXTRAÇÃO AUTENTICADA\nID: {_safe_sheet_value(meta.get('job_id'))}"
    seal.font = Font(bold=True, size=14, color=red)
    seal.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    seal.fill = PatternFill("solid", fgColor="FFF5F5")
    seal.border = Border(top=thin, left=thin, right=thin, bottom=thin)


def dataframe_to_excel_bytes(df: pd.DataFrame, metadata: dict | None = None) -> bytes:
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        _add_autenticidade_sheet(writer, metadata)

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
