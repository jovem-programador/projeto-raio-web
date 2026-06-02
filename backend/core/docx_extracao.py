import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from core.scriptTela import ALIASES, CAMPOS_ORDEM, normalize, pick_value_after_key


WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _texts_from_xml(data: bytes) -> list[str]:
    root = ET.fromstring(data)
    return [_clean_text(node.text) for node in root.iter(f"{WORD_NS}t") if _clean_text(node.text)]


def _tables_from_xml(data: bytes) -> list[list[list[str]]]:
    root = ET.fromstring(data)
    tables: list[list[list[str]]] = []
    for tbl in root.iter(f"{WORD_NS}tbl"):
        rows: list[list[str]] = []
        for tr in tbl.iter(f"{WORD_NS}tr"):
            cells: list[str] = []
            for tc in tr.iter(f"{WORD_NS}tc"):
                text = " ".join(_clean_text(node.text) for node in tc.iter(f"{WORD_NS}t") if _clean_text(node.text))
                cells.append(_clean_text(text))
            rows.append(cells)
        tables.append(rows)
    return tables


def _read_docx(docx_path: str) -> tuple[list[str], list[str], list[list[list[str]]]]:
    header_texts: list[str] = []
    body_texts: list[str] = []
    tables: list[list[list[str]]] = []

    with ZipFile(docx_path) as archive:
        for name in archive.namelist():
            if name == "word/document.xml" or (name.startswith("word/header") and name.endswith(".xml")):
                data = archive.read(name)
                texts = _texts_from_xml(data)
                tables.extend(_tables_from_xml(data))
                if name.startswith("word/header"):
                    header_texts.extend(texts)
                else:
                    body_texts.extend(texts)

    return header_texts, body_texts, tables


def _next_value(texts: list[str], aliases: list[str]) -> str:
    aliases_norm = {normalize(alias) for alias in aliases}
    for idx, text in enumerate(texts[:-1]):
        if normalize(text) in aliases_norm:
            return texts[idx + 1]
    return ""


def _doc_number_from_filename(docx_path: str) -> str:
    stem = Path(docx_path).stem.upper()
    match = re.search(r"((?:MC-)?[0-9]{4,}[A-Z]{2}-[A-Z]-[0-9]{5,})", stem)
    return match.group(1) if match else ""


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
    campos_textuais = [
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

    for campo in campos_textuais:
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
    for line in lines:
        up = normalize(line)

        if not carimbo.get("1a_REV"):
            match = re.search(r"\b1\s*[Aª]?\s*REV(?:ISAO|ISÃO)?\b[\s:=-]*(.+)$", up)
            if match:
                carimbo["1a_REV"] = match.group(1).strip()

        if not carimbo.get("2a_REV"):
            match = re.search(r"\b2\s*[Aª]?\s*REV(?:ISAO|ISÃO)?\b[\s:=-]*(.+)$", up)
            if match:
                carimbo["2a_REV"] = match.group(1).strip()


def _seed_from_filename(docx_path: str, carimbo: dict):
    if not carimbo.get("NUMERO_VALE"):
        carimbo["NUMERO_VALE"] = _doc_number_from_filename(docx_path)

    if not carimbo.get("1a_REV"):
        match = re.search(r"(?:^|[_\-\s])REV(?:IS[ÃA]O)?[_\-\s\.]*([A-Z0-9]+)$", Path(docx_path).stem.upper())
        if match:
            carimbo["1a_REV"] = match.group(1).strip()


def _fill_header_fields(header_texts: list[str], carimbo: dict):
    if not header_texts:
        return

    if not carimbo.get("CLASSIFICAÇÃO"):
        carimbo["CLASSIFICAÇÃO"] = _next_value(header_texts, ["CLASSIFICAÇÃO", "CLASSIFICACAO"])

    if not carimbo.get("NUMERO_VALE"):
        carimbo["NUMERO_VALE"] = _next_value(header_texts, ["Nº VALE", "N° VALE", "N VALE", "VALE"])

    if not carimbo.get("NÚMERO_DA_CONTRATADA"):
        carimbo["NÚMERO_DA_CONTRATADA"] = _next_value(
            header_texts,
            ["Nº (CONTRATADA)", "N° (CONTRATADA)", "Nº CONTRATADA", "N° CONTRATADA", "N CONTRATADA"],
        )

    if not carimbo.get("1a_REV"):
        carimbo["1a_REV"] = _next_value(header_texts, ["REV.", "REV", "REVISÃO", "REVISAO"])

    class_idx = next((i for i, text in enumerate(header_texts) if normalize(text) in {"CLASSIFICAÇÃO", "CLASSIFICACAO"}), -1)
    vale_idx = next((i for i, text in enumerate(header_texts) if normalize(text) in {"N VALE", "NO VALE", "Nº VALE"}), -1)
    middle = header_texts[class_idx + 2:vale_idx] if class_idx >= 0 and vale_idx > class_idx else []
    middle = [text for text in middle if normalize(text) not in {"PAGINA", "/", "N VALE", "REV"}]

    if not middle:
        return

    if not carimbo.get("PROJETO") and len(middle) >= 1:
        carimbo["PROJETO"] = middle[0]

    if not carimbo.get("N_PROJ_SE"):
        for idx, text in enumerate(middle):
            up = normalize(text)
            if up in {"SE", "SE-"} and idx + 1 < len(middle):
                carimbo["N_PROJ_SE"] = middle[idx + 1].strip()
                break
            if re.fullmatch(r"SE[-\s]*\d+", up):
                carimbo["N_PROJ_SE"] = re.sub(r"^SE[-\s]*", "", text, flags=re.IGNORECASE).strip()
                break

    # Remove o par SE/numero para mapear as linhas textuais do cabeçalho.
    filtered: list[str] = []
    skip_next = False
    for idx, text in enumerate(middle):
        if skip_next:
            skip_next = False
            continue
        if normalize(text) in {"SE", "SE-"} and idx + 1 < len(middle):
            skip_next = True
            continue
        filtered.append(text)

    if len(filtered) > 1 and not carimbo.get("FASE_DO_PROJETO"):
        carimbo["FASE_DO_PROJETO"] = filtered[1]
    if len(filtered) > 2 and not carimbo.get("ÁREA_E/OU_SUBÁREA"):
        carimbo["ÁREA_E/OU_SUBÁREA"] = filtered[2]
    if len(filtered) > 3 and not carimbo.get("TÍTULO_DO_DESENHO"):
        carimbo["TÍTULO_DO_DESENHO"] = filtered[3]
    if len(filtered) > 4 and not carimbo.get("SUBTÍTULO_1_DO_DESENHO"):
        carimbo["SUBTÍTULO_1_DO_DESENHO"] = filtered[4]
    if len(filtered) > 5 and not carimbo.get("SUBTÍTULO_2_DO_DESENHO"):
        carimbo["SUBTÍTULO_2_DO_DESENHO"] = " ".join(filtered[5:]).strip()


def _fill_revisions_from_tables(tables: list[list[list[str]]], carimbo: dict):
    for table in tables:
        for idx, row in enumerate(table):
            row_norm = [normalize(cell) for cell in row]
            if not any(cell.startswith("REV") for cell in row_norm) or "TE" not in row_norm:
                continue

            for data_row in table[idx + 1:]:
                values = [cell for cell in data_row if cell.strip()]
                if len(values) < 3:
                    continue

                if not carimbo.get("1a_REV"):
                    carimbo["1a_REV"] = values[0]
                if not carimbo.get("EMIS_1"):
                    carimbo["EMIS_1"] = values[1]
                if not carimbo.get("DESCRIÇÃO_DA_REVISÃO_1"):
                    carimbo["DESCRIÇÃO_DA_REVISÃO_1"] = values[2]
                return


def extrair_carimbo_de_um_docx(docx_path: str) -> dict | None:
    carimbo = {c: "" for c in CAMPOS_ORDEM}
    carimbo["Nome_Arquivo"] = os.path.basename(docx_path)
    carimbo["_LAYOUT_ESCOLHIDO"] = "DOCX"

    header_texts, _body_texts, tables = _read_docx(docx_path)
    header_lines = [_clean_text(line) for line in header_texts if _clean_text(line)]

    _fill_header_fields(header_texts, carimbo)
    _fill_by_key_value_lines(header_lines, carimbo)
    _fill_revisions_from_tables(tables, carimbo)
    _fill_revisions_from_lines(header_lines, carimbo)
    _seed_from_filename(docx_path, carimbo)

    if normalize(carimbo.get("N_CONTRATO", "")) in {"-", "SE", "SE-"}:
        carimbo["N_CONTRATO"] = ""

    if (
        carimbo.get("PROJETO")
        or carimbo.get("NUMERO_VALE")
        or carimbo.get("1a_REV")
        or carimbo.get("N_PROJ_SE")
    ):
        return carimbo
    return None


def _converter_doc_para_docx(doc_path: Path, output_dir: Path) -> Path:
    converter = shutil.which("libreoffice") or shutil.which("soffice") or shutil.which("lowriter")
    if not converter:
        raise RuntimeError("LibreOffice não encontrado para converter arquivos .doc")

    env = os.environ.copy()
    env.setdefault("HOME", str(output_dir))

    subprocess.run(
        [
            converter,
            "--headless",
            "--convert-to",
            "docx",
            "--outdir",
            str(output_dir),
            str(doc_path),
        ],
        check=True,
        timeout=120,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    converted_path = output_dir / f"{doc_path.stem}.docx"
    if not converted_path.exists():
        raise RuntimeError(f"Conversão DOC para DOCX não gerou arquivo para: {doc_path.name}")
    return converted_path


def extrair_carimbo_de_um_doc(doc_path: str) -> dict | None:
    with tempfile.TemporaryDirectory() as tmp:
        converted_path = _converter_doc_para_docx(Path(doc_path), Path(tmp))
        carimbo = extrair_carimbo_de_um_docx(str(converted_path))
        if carimbo:
            carimbo["Nome_Arquivo"] = os.path.basename(doc_path)
            carimbo["_LAYOUT_ESCOLHIDO"] = "DOC"
        return carimbo


def extrair_dados_completos_de_pasta_docx(pasta_docx: Path):
    resultados = []
    arquivos = sorted([p for p in pasta_docx.iterdir() if p.is_file() and p.suffix.lower() in {".doc", ".docx"}])

    for path in arquivos:
        if path.suffix.lower() == ".doc":
            carimbo = extrair_carimbo_de_um_doc(str(path))
        else:
            carimbo = extrair_carimbo_de_um_docx(str(path))
        if carimbo:
            resultados.append(carimbo)

    return resultados
