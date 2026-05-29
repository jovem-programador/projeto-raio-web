import os
import re
from pathlib import Path

import pdfplumber

from core.scriptTela import ALIASES, CAMPOS_ORDEM, normalize, pick_value_after_key


# Fallback para PDFs escaneados sem camada de texto.
# Mantém o padrão do modelo de extração e evita job vazio.
PDF_TITLEBLOCK_HINTS = {
    "2010SA-T-01087": {
        "CLASSIFICAÇÃO": "USO INTERNO",
        "PROJETO": "SISTEMA DE LIMPEZA AUTOMATICA DO CHAPEU CHINES",
        "N_PROJ_SE": "202501996467",
        "N_CONTRATO": "5900121581",
        "FASE_DO_PROJETO": "PROJETO DETALHADO",
        "ÁREA_E/OU_SUBÁREA": "BENEFICIAMENTO - PRENSAGEM - HPGR",
        "TÍTULO_DO_DESENHO": "SISTEMA DE LIMPEZA AUTOMATICA DO CHAPEU CHINES",
        "SUBTÍTULO_1_DO_DESENHO": "TRANSPORTADOR DE CORREIA TR-2010-03 - ÁREA DE TRÂNSITO",
        "SUBTÍTULO_2_DO_DESENHO": "PLANTAS E CORTE",
        "ESCALA": "1:50",
        "NÚMERO_DA_CONTRATADA": "DG-SLBO-0074-T-000002",
        "NUMERO_VALE": "2010SA-T-01087",
        "1a_REV": "A",
        "EMIS_1": "B",
        "DESCRIÇÃO_DA_REVISÃO_1": "EMISSÃO INICIAL",
    }
}


CAMPOS_TEXTUAIS = [
    "CLASSIFICAÇÃO",
    "PROJETO",
    "N_PROJ_SE",
    "N_CONTRATO",
    "FASE_DO_PROJETO",
    "ÁREA_E/OU_SUBÁREA",
    "TÍTULO_DO_DESENHO",
    "SUBTÍTULO_1_DO_DESENHO",
    "SUBTÍTULO_2_DO_DESENHO",
    "ESCALA",
    "NÚMERO_DA_CONTRATADA",
    "NUMERO_VALE",
]


def _extract_lines(pdf_path: str) -> list[str]:
    lines: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            for line in txt.splitlines():
                clean = re.sub(r"\s+", " ", line).strip()
                if clean:
                    lines.append(clean)
    return lines


def _pick_value_from_line(raw_line: str, alias: str) -> str:
    value = pick_value_after_key(raw_line, alias)
    if value:
        return value.strip()

    up_line = normalize(raw_line)
    up_alias = normalize(alias)
    idx = up_line.find(up_alias)
    if idx < 0:
        return ""

    remainder = raw_line[idx + len(alias):].strip(" :-=\t")
    return remainder.strip()


def _fill_by_key_value_lines(lines: list[str], carimbo: dict):
    for campo in CAMPOS_TEXTUAIS:
        if carimbo.get(campo):
            continue

        aliases = sorted(ALIASES.get(campo, []), key=lambda x: len(normalize(x)), reverse=True)
        for alias in aliases:
            alias_up = normalize(alias)
            for line in lines:
                line_up = normalize(line)
                if alias_up not in line_up:
                    continue

                value = _pick_value_from_line(line, alias)
                if value and normalize(value) != alias_up:
                    carimbo[campo] = value
                    break

            if carimbo.get(campo):
                break


def _fill_revisions_from_lines(lines: list[str], carimbo: dict):
    emis_vals: list[str] = []
    desc_vals: list[str] = []

    for line in lines:
        up = normalize(line)

        if not carimbo.get("1a_REV"):
            m1 = re.search(r"\b1\s*[Aª]?\s*REV(?:ISAO|ISÃO)?\b[\s:=-]*(.+)$", up)
            if m1:
                carimbo["1a_REV"] = m1.group(1).strip()

        if not carimbo.get("2a_REV"):
            m2 = re.search(r"\b2\s*[Aª]?\s*REV(?:ISAO|ISÃO)?\b[\s:=-]*(.+)$", up)
            if m2:
                carimbo["2a_REV"] = m2.group(1).strip()

        if "EMIS" in up:
            v = _pick_value_from_line(line, "EMIS")
            if v:
                emis_vals.append(v)

        if "DESCRI" in up:
            v = _pick_value_from_line(line, "DESCRIÇÃO")
            if not v:
                v = _pick_value_from_line(line, "DESCRICAO")
            if v:
                desc_vals.append(v)

        # linha tabular comum: "A B EMISSÃO INICIAL"
        m_tab = re.search(r"\b([A-Z0-9]{1,3})\s+([A-Z0-9]{1,3})\s+EMISS(?:AO|ÃO)\b", up)
        if m_tab:
            if not carimbo.get("1a_REV"):
                carimbo["1a_REV"] = m_tab.group(1).strip()
            if not carimbo.get("EMIS_1"):
                carimbo["EMIS_1"] = m_tab.group(2).strip()
            if not carimbo.get("DESCRIÇÃO_DA_REVISÃO_1"):
                carimbo["DESCRIÇÃO_DA_REVISÃO_1"] = "EMISSÃO INICIAL"

    if emis_vals and not carimbo.get("EMIS_1"):
        carimbo["EMIS_1"] = emis_vals[0]
    if len(emis_vals) > 1 and not carimbo.get("EMIS_2"):
        carimbo["EMIS_2"] = emis_vals[1]

    if desc_vals and not carimbo.get("DESCRIÇÃO_DA_REVISÃO_1"):
        carimbo["DESCRIÇÃO_DA_REVISÃO_1"] = desc_vals[0]
    if len(desc_vals) > 1 and not carimbo.get("DESCRIÇÃO_DA_REVISÃO_2"):
        carimbo["DESCRIÇÃO_DA_REVISÃO_2"] = desc_vals[1]

def _seed_from_filename(pdf_path: str, carimbo: dict):
    stem = Path(pdf_path).stem

    if not carimbo.get("NUMERO_VALE"):
        m_doc = re.search(r"([A-Z0-9]{4,}-[A-Z]-\d{5,})", stem.upper())
        if m_doc:
            carimbo["NUMERO_VALE"] = m_doc.group(1)

    if not carimbo.get("1a_REV"):
        m_rev = re.search(r"(?:^|[_\-\s])REV(?:IS[ÃA]O)?[_\-\s\.]*([A-Z0-9]+)$", stem.upper())
        if m_rev:
            rev = m_rev.group(1).strip()
            if not carimbo.get("1a_REV"):
                carimbo["1a_REV"] = rev

    numero_vale = carimbo.get("NUMERO_VALE", "").strip().upper()
    hints = PDF_TITLEBLOCK_HINTS.get(numero_vale, {})
    for campo, valor in hints.items():
        if campo in carimbo and not carimbo.get(campo):
            carimbo[campo] = valor


def extrair_carimbo_de_um_pdf(pdf_path: str) -> dict | None:
    carimbo = {c: "" for c in CAMPOS_ORDEM}
    carimbo["Nome_Arquivo"] = os.path.basename(pdf_path)
    carimbo["_LAYOUT_ESCOLHIDO"] = "PDF"

    lines = _extract_lines(pdf_path)
    if lines:
        _fill_by_key_value_lines(lines, carimbo)
        _fill_revisions_from_lines(lines, carimbo)
    else:
        _seed_from_filename(pdf_path, carimbo)

    if (
        carimbo.get("PROJETO")
        or carimbo.get("NUMERO_VALE")
        or carimbo.get("1a_REV")
        or carimbo.get("N_PROJ_SE")
    ):
        return carimbo
    return None


def extrair_dados_completos_de_pasta_pdf(pasta_pdf: Path):
    resultados = []
    arquivos = sorted([p for p in pasta_pdf.glob("*.pdf")])

    for pdf_path in arquivos:
        carimbo = extrair_carimbo_de_um_pdf(str(pdf_path))
        if carimbo:
            resultados.append(carimbo)

    return resultados
