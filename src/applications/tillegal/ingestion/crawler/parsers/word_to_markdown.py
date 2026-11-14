"""Extract text and basic structure from legacy DOC and DOCX legal documents."""

from __future__ import annotations

import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import BinaryIO

_WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_W = f"{{{_WORD_NS}}}"
_BOLD = f"{_W}b"
_ITALIC = f"{_W}i"


class LegacyDocConverterUnavailableError(RuntimeError):
    """Raised when the worker cannot find antiword for a legacy DOC file."""


def convert_word_to_markdown(content: bytes, file_name: str, timeout_seconds: float = 60) -> str:
    """Convert a DOCX package or legacy DOC file into UTF-8 Markdown."""
    extension = Path(file_name).suffix.lower()
    if extension == ".docx":
        markdown = _convert_docx(content)
    elif extension == ".doc":
        markdown = _convert_legacy_doc(content, file_name, timeout_seconds)
    else:
        raise ValueError(f"Unsupported VBPL Word attachment format: {extension or '(no extension)'}")
    markdown = re.sub(
        r"\n{3,}",
        "\n\n",
        markdown.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n\n"),
    ).strip()
    if not markdown:
        raise ValueError(f"VBPL Word attachment produced empty Markdown: {file_name}")
    return f"{markdown}\n"


def _convert_docx(content: bytes) -> str:
    try:
        with zipfile.ZipFile(_bytes_file(content)) as archive:
            document = ET.fromstring(archive.read("word/document.xml"))
    except (KeyError, OSError, ET.ParseError, zipfile.BadZipFile) as error:
        raise ValueError("VBPL DOCX attachment is invalid or missing word/document.xml") from error

    body = document.find(f".//{_W}body")
    if body is None:
        raise ValueError("VBPL DOCX attachment has no document body")
    blocks = [_render_docx_block(child) for child in body]
    return "\n\n".join(block for block in blocks if block)


def _bytes_file(content: bytes) -> BinaryIO:
    from io import BytesIO

    return BytesIO(content)


def _render_docx_block(element: ET.Element) -> str:
    if element.tag == f"{_W}p":
        text = _render_docx_paragraph(element)
        properties = element.find(f"{_W}pPr/{_W}pStyle")
        style = properties.get(f"{_W}val", "") if properties is not None else ""
        if text and style.lower().startswith("heading"):
            level = re.search(r"\d+", style)
            if level is not None:
                return f"{'#' * min(int(level.group()), 6)} {text}"
        return text
    if element.tag == f"{_W}tbl":
        return _render_docx_table(element)
    return ""


def _render_docx_paragraph(paragraph: ET.Element) -> str:
    parts: list[str] = []
    for run in paragraph.iter(f"{_W}r"):
        run_properties = run.find(f"{_W}rPr")
        text_parts: list[str] = []
        for child in run:
            if child.tag == f"{_W}t":
                text_parts.append(child.text or "")
            elif child.tag == f"{_W}tab":
                text_parts.append("    ")
            elif child.tag in {f"{_W}br", f"{_W}cr"}:
                text_parts.append("\n")
        text = "".join(text_parts)
        if run_properties is not None and text.strip():
            # Run boundaries are formatting boundaries, not word boundaries.
            # Keep whitespace outside emphasis markers so Markdown remains valid.
            leading = text[: len(text) - len(text.lstrip())]
            trailing = text[len(text.rstrip()) :]
            core = text.strip()
            if _has_enabled_property(run_properties, _BOLD):
                core = f"**{core}**"
            if _has_enabled_property(run_properties, _ITALIC):
                core = f"*{core}*"
            text = f"{leading}{core}{trailing}"
        parts.append(text)

    paragraph_text = "".join(parts).strip()
    if not paragraph_text:
        return ""
    if paragraph.find(f"{_W}pPr/{_W}numPr") is not None:
        return f"- {paragraph_text}"
    return paragraph_text


def _has_enabled_property(properties: ET.Element, tag: str) -> bool:
    value = properties.find(tag)
    return value is not None and value.get(f"{_W}val", "1") not in {"0", "false", "off"}


def _render_docx_table(table: ET.Element) -> str:
    rows: list[list[str]] = []
    for row in table.findall(f"{_W}tr"):
        cells: list[str] = []
        for cell in row.findall(f"{_W}tc"):
            paragraphs = [_render_docx_paragraph(paragraph) for paragraph in cell.findall(f"{_W}p")]
            cells.append("<br>".join(paragraph for paragraph in paragraphs if paragraph))
        if cells:
            rows.append(cells)
    if not rows:
        return ""

    column_count = max(map(len, rows))
    lines: list[str] = []
    for index, row in enumerate(rows):
        padded = row + [""] * (column_count - len(row))
        lines.append("| " + " | ".join(_escape_cell(cell) for cell in padded) + " |")
        if index == 0:
            lines.append("| " + " | ".join("---" for _ in range(column_count)) + " |")
    return "\n".join(lines)


def _escape_cell(value: str) -> str:
    return value.replace("|", r"\|")


def _convert_legacy_doc(content: bytes, file_name: str, timeout_seconds: float) -> str:
    if not content.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        raise ValueError(f"VBPL DOC attachment is not an OLE Word document: {file_name}")
    try:
        with tempfile.TemporaryDirectory(prefix="vbpl-doc-") as directory:
            document_path = Path(directory) / "source.doc"
            document_path.write_bytes(content)
            result = subprocess.run(
                ["antiword", "-t", str(document_path)],
                check=False,
                capture_output=True,
                timeout=timeout_seconds,
            )
    except FileNotFoundError as error:
        raise LegacyDocConverterUnavailableError(
            "Legacy VBPL .doc conversion requires antiword to be installed on the worker"
        ) from error
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"Legacy VBPL .doc conversion timed out: {file_name}") from error

    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Legacy VBPL .doc conversion failed for {file_name}: {detail or result.returncode}")
    try:
        return result.stdout.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(f"Legacy VBPL .doc conversion returned invalid UTF-8: {file_name}") from error
