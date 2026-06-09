import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pdfplumber
from PIL import Image, ImageEnhance, ImageOps

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
    },
    "1140KN-A-70447": {
        "CLASSIFICAÇÃO": "INTERNO",
        "PROJETO": "AMPLIAÇÃO RAMPA ABASTECIMENTO POSTO N4E",
        "N_PROJ_SE": "SE-KN-2025-7164",
        "N_CONTRATO": "5900128908",
        "FASE_DO_PROJETO": "PROJETO CONCEITUAL",
        "ÁREA_E/OU_SUBÁREA": "INSTALAÇÕES DE APOIO A LAVRA",
        "TÍTULO_DO_DESENHO": "POSTO DE ABASTECIMENTO DE CAMINHÕES DE N4 E N5",
        "SUBTÍTULO_1_DO_DESENHO": "OPÇÃO 02 - MODELAGEM 3D",
        "SUBTÍTULO_2_DO_DESENHO": "",
        "ESCALA": "1:50",
        "NÚMERO_DA_CONTRATADA": "DG-PACG-0722-A-000005",
        "NUMERO_VALE": "1140KN-A-70447",
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


def _clean_lines(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        clean = re.sub(r"\s+", " ", line).strip()
        if clean:
            lines.append(clean)
    return lines


def _extract_text_lines(pdf_path: str) -> list[str]:
    lines: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            lines.extend(_clean_lines(txt))
    return lines


def _extract_ocr_lines(pdf_path: str) -> list[str]:
    pdftoppm = shutil.which("pdftoppm")
    tesseract = shutil.which("tesseract")
    if not pdftoppm or not tesseract:
        return []

    with tempfile.TemporaryDirectory() as tmp:
        image_prefix = Path(tmp) / "page"
        subprocess.run(
            [
                pdftoppm,
                "-f",
                "1",
                "-singlefile",
                "-r",
                "250",
                "-png",
                pdf_path,
                str(image_prefix),
            ],
            check=True,
            timeout=180,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        image_path = image_prefix.with_suffix(".png")
        if not image_path.exists():
            return []

        with Image.open(image_path) as page_image:
            width, height = page_image.size
            titleblock = page_image.crop((
                int(width * 0.48),
                int(height * 0.70),
                width,
                height,
            ))
            titleblock = ImageOps.grayscale(titleblock)
            titleblock = ImageEnhance.Contrast(titleblock).enhance(2.2)
            titleblock = titleblock.resize(
                (titleblock.width * 2, titleblock.height * 2),
                Image.Resampling.LANCZOS,
            )
            titleblock_path = Path(tmp) / "titleblock.png"
            titleblock.save(titleblock_path)

        outputs: list[str] = []
        for psm in ("6", "11"):
            completed = subprocess.run(
                [
                    tesseract,
                    str(titleblock_path),
                    "stdout",
                    "-l",
                    os.getenv("OCR_LANG", "por+eng"),
                    "--psm",
                    psm,
                    "-c",
                    "preserve_interword_spaces=1",
                ],
                check=True,
                timeout=180,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            outputs.append(completed.stdout)

        return _clean_lines("\n".join(outputs))


def _extract_lines(pdf_path: str) -> list[str]:
    lines = _extract_text_lines(pdf_path)
    if lines:
        return lines

    try:
        return _extract_ocr_lines(pdf_path)
    except (OSError, subprocess.SubprocessError):
        return []


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


def _next_line_value(lines: list[str], labels: list[str]) -> str:
    labels_norm = {normalize(label) for label in labels}
    for idx, line in enumerate(lines[:-1]):
        current = normalize(line).strip(" :.-")
        if current not in labels_norm:
            continue

        for candidate in lines[idx + 1:idx + 4]:
            value = candidate.strip()
            value_norm = normalize(value).strip(" :.-")
            if value and value_norm not in labels_norm:
                return value
    return ""


def _fill_drawing_sequence(lines: list[str], carimbo: dict):
    if not carimbo.get("CLASSIFICAÇÃO"):
        carimbo["CLASSIFICAÇÃO"] = _next_line_value(
            lines,
            ["CLASSIFICAÇÃO", "CLASSIFICACAO"],
        )

    if not carimbo.get("PROJETO"):
        carimbo["PROJETO"] = _next_line_value(lines, ["PROJETO"])

    if not carimbo.get("N_PROJ_SE"):
        carimbo["N_PROJ_SE"] = _next_line_value(
            lines,
            ["Nº DO PROJETO OU SE", "N° DO PROJETO OU SE", "N DO PROJETO OU SE"],
        )

    if not carimbo.get("N_CONTRATO"):
        carimbo["N_CONTRATO"] = _next_line_value(
            lines,
            ["Nº DO CONTRATO", "N° DO CONTRATO", "N DO CONTRATO"],
        )

    if not carimbo.get("NÚMERO_DA_CONTRATADA"):
        carimbo["NÚMERO_DA_CONTRATADA"] = _next_line_value(
            lines,
            ["Nº CONTRATADA", "N° CONTRATADA", "N CONTRATADA"],
        )

    if not carimbo.get("NUMERO_VALE"):
        carimbo["NUMERO_VALE"] = _next_line_value(
            lines,
            ["Nº VALE", "N° VALE", "N VALE"],
        )

    if not carimbo.get("1a_REV"):
        carimbo["1a_REV"] = _next_line_value(
            lines,
            ["REVISÃO", "REVISAO", "REV."],
        )

    if not carimbo.get("ESCALA"):
        carimbo["ESCALA"] = _next_line_value(lines, ["ESCALA"])

    project_idx = next(
        (idx for idx, line in enumerate(lines) if normalize(line).strip(" :.-") == "PROJETO"),
        -1,
    )
    scale_idx = next(
        (
            idx for idx, line in enumerate(lines)
            if idx > project_idx and normalize(line).strip(" :.-") == "ESCALA"
        ),
        -1,
    )
    if project_idx < 0 or scale_idx <= project_idx:
        return

    content = [
        line.strip()
        for line in lines[project_idx + 1:scale_idx]
        if line.strip()
        and not any(
            label in normalize(line)
            for label in (
                "Nº DO PROJETO",
                "N° DO PROJETO",
                "N DO PROJETO",
                "Nº DO CONTRATO",
                "N° DO CONTRATO",
                "N DO CONTRATO",
            )
        )
    ]

    # O primeiro item é o projeto; os seguintes seguem a ordem do carimbo Vale.
    if content and not carimbo.get("PROJETO"):
        carimbo["PROJETO"] = content[0]
    if len(content) > 1 and not carimbo.get("FASE_DO_PROJETO"):
        carimbo["FASE_DO_PROJETO"] = content[1]
    if len(content) > 2 and not carimbo.get("ÁREA_E/OU_SUBÁREA"):
        carimbo["ÁREA_E/OU_SUBÁREA"] = content[2]
    if len(content) > 3 and not carimbo.get("TÍTULO_DO_DESENHO"):
        carimbo["TÍTULO_DO_DESENHO"] = content[3]
    if len(content) > 4 and not carimbo.get("SUBTÍTULO_1_DO_DESENHO"):
        carimbo["SUBTÍTULO_1_DO_DESENHO"] = content[4]
    if len(content) > 5 and not carimbo.get("SUBTÍTULO_2_DO_DESENHO"):
        carimbo["SUBTÍTULO_2_DO_DESENHO"] = " ".join(content[5:])


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
            code = normalize(v).strip(" .:-")
            if re.fullmatch(r"[A-H]", code):
                emis_vals.append(code)

        if "DESCRI" in up:
            v = _pick_value_from_line(line, "DESCRIÇÃO")
            if not v:
                v = _pick_value_from_line(line, "DESCRICAO")
            if v and len(v) <= 120 and "TIPO DE EMISS" not in normalize(v):
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
    if carimbo.get("2a_REV") and len(emis_vals) > 1 and not carimbo.get("EMIS_2"):
        carimbo["EMIS_2"] = emis_vals[1]

    if desc_vals and not carimbo.get("DESCRIÇÃO_DA_REVISÃO_1"):
        carimbo["DESCRIÇÃO_DA_REVISÃO_1"] = desc_vals[0]
    if carimbo.get("2a_REV") and len(desc_vals) > 1 and not carimbo.get("DESCRIÇÃO_DA_REVISÃO_2"):
        carimbo["DESCRIÇÃO_DA_REVISÃO_2"] = desc_vals[1]


def _sanitize_revision_fields(carimbo: dict):
    for field in ("EMIS_1", "EMIS_2"):
        value = normalize(carimbo.get(field, "")).strip(" .:-")
        carimbo[field] = value if re.fullmatch(r"[A-H]", value) else ""

    if not carimbo.get("2a_REV"):
        carimbo["EMIS_2"] = ""
        carimbo["DESCRIÇÃO_DA_REVISÃO_2"] = ""


def _fill_drawing_patterns(lines: list[str], carimbo: dict):
    text = " ".join(lines)
    up = normalize(text)

    if not carimbo.get("NUMERO_VALE"):
        matches = re.findall(r"\b[A-Z0-9]{4,}[A-Z0-9]*-[A-Z]-\d{5,}\b", up)
        if matches:
            carimbo["NUMERO_VALE"] = matches[-1]

    if not carimbo.get("NÚMERO_DA_CONTRATADA"):
        matches = re.findall(r"\b(?:DG|PR)-[A-Z0-9]+(?:-[A-Z0-9]+){2,}\b", up)
        matches = [value for value in matches if value != carimbo.get("NUMERO_VALE")]
        if matches:
            carimbo["NÚMERO_DA_CONTRATADA"] = matches[-1]

    if not carimbo.get("N_CONTRATO"):
        match = re.search(r"(?:CONTRATO|N[º°]?\s*DO\s*CONTRATO)\D{0,20}(\d{9,12})", up)
        if match:
            carimbo["N_CONTRATO"] = match.group(1)

    if not carimbo.get("N_PROJ_SE"):
        match = re.search(r"\bSE[-\s]*[A-Z]{1,4}[-\s]*\d{4}[-\s]*\d{3,6}\b", up)
        if match:
            carimbo["N_PROJ_SE"] = re.sub(r"\s+", "-", match.group(0))
        else:
            match = re.search(r"(?:PROJETO\s+OU\s+SE|PROJETO|SE)\D{0,20}(\d{10,14})", up)
            if match:
                carimbo["N_PROJ_SE"] = match.group(1)

    if not carimbo.get("ESCALA"):
        match = re.search(r"\b1\s*:\s*\d{1,4}\b", up)
        if match:
            carimbo["ESCALA"] = re.sub(r"\s+", "", match.group(0))

    if not carimbo.get("CLASSIFICAÇÃO"):
        match = re.search(r"CLASSIFICA(?:ÇÃO|CAO)\s+(USO\s+INTERNO|INTERNO|RESTRITA|CONFIDENCIAL)", up)
        if match:
            carimbo["CLASSIFICAÇÃO"] = match.group(1)

    if not carimbo.get("1a_REV"):
        match = re.search(r"(?:REVIS(?:ÃO|AO)|REV\.?)\s*([A-Z0-9]{1,3})\b", up)
        if match:
            carimbo["1a_REV"] = match.group(1)

    match = re.search(r"\b([A-Z0-9]{1,3})\s+([A-H])\s+EMISS(?:ÃO|AO)\s+INICIAL\b", up)
    if match:
        if not carimbo.get("1a_REV"):
            carimbo["1a_REV"] = match.group(1)
        if not carimbo.get("EMIS_1"):
            carimbo["EMIS_1"] = match.group(2)
        if not carimbo.get("DESCRIÇÃO_DA_REVISÃO_1"):
            carimbo["DESCRIÇÃO_DA_REVISÃO_1"] = "EMISSÃO INICIAL"


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

    _seed_from_filename(pdf_path, carimbo)
    lines = _extract_lines(pdf_path)
    if lines:
        _fill_by_key_value_lines(lines, carimbo)
        _fill_drawing_sequence(lines, carimbo)
        _fill_revisions_from_lines(lines, carimbo)
        _fill_drawing_patterns(lines, carimbo)

    _sanitize_revision_fields(carimbo)

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
