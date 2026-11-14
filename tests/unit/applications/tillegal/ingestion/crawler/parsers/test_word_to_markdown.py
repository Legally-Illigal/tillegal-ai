import subprocess
from io import BytesIO
from pathlib import Path
from uuid import UUID
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from src.applications.tillegal.ingestion.crawler.parsers.legal_markdown import parse_legal_markdown
from src.applications.tillegal.ingestion.crawler.parsers.word_to_markdown import (
    LegacyDocConverterUnavailableError,
    convert_word_to_markdown,
)

_WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _docx_with_body(body: str) -> bytes:
    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as docx:
        docx.writestr("word/document.xml", f'<w:document xmlns:w="{_WORD_NS}"><w:body>{body}</w:body></w:document>')
    return archive.getvalue()


@pytest.mark.parametrize("properties,marker", [("", ""), ("<w:b/>", "**"), ("<w:i/>", "*"), ("<w:b/><w:i/>", "***")])
def test_preserves_whitespace_around_formatted_runs(properties: str, marker: str) -> None:
    body = (
        '<w:p><w:r><w:t>Ủy</w:t></w:r>'
        f'<w:r><w:rPr>{properties}</w:rPr><w:t xml:space="preserve"> viên </w:t></w:r>'
        '<w:r><w:t>Ủy ban</w:t></w:r></w:p>'
    )
    assert convert_word_to_markdown(_docx_with_body(body), "source.docx") == f"Ủy {marker}viên{marker} Ủy ban\n"


@pytest.mark.parametrize("parts", [("Trá", "ch"), ("Điều\u00a0", "8"), ("Ủy", " ", "viên")])
def test_preserves_text_across_unformatted_runs(parts: tuple[str, ...]) -> None:
    runs = ''.join(f'<w:r><w:t xml:space="preserve">{escape(part)}</w:t></w:r>' for part in parts)
    assert convert_word_to_markdown(_docx_with_body(f"<w:p>{runs}</w:p>"), "source.docx") == ''.join(parts) + "\n"


def test_split_bold_article_heading_keeps_clauses_in_the_correct_article() -> None:
    body = '<w:p><w:r><w:t>Chương II. Công việc</w:t></w:r></w:p>'
    for number in (7, 8):
        runs = ''.join(
            f'<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{part}</w:t></w:r>'
            for part in ("Điều ", str(number), ". Trách nhiệm của Ủy", " viên", " Ủy ban")
        )
        body += f'<w:p>{runs}</w:p><w:p><w:r><w:t>2. Nội dung khoản {number}</w:t></w:r></w:p>'
        body += '<w:p><w:r><w:t>a) Nội dung điểm</w:t></w:r></w:p>'
    markdown = convert_word_to_markdown(_docx_with_body(body), "source.docx")
    parsed = parse_legal_markdown(markdown, source_document_id=UUID(int=1), title="Quy chế")
    articles = [node for node in parsed.nodes if node.kind == "article"]
    assert [node.label for node in articles] == [
        f"Điều {number}: Trách nhiệm của Ủy viên Ủy ban" for number in (7, 8)
    ]
    assert [node.node_id for node in parsed.nodes if node.kind == "clause"] == [
        f"chapter-ii-article-{number}-clause-2" for number in (7, 8)
    ]
    assert [node.parent_node_id for node in parsed.nodes if node.kind == "point"] == [
        f"chapter-ii-article-{number}-clause-2" for number in (7, 8)
    ]


def _docx_bytes() -> bytes:
    document = f"""<?xml version="1.0" encoding="UTF-8"?>
    <w:document xmlns:w="{_WORD_NS}"><w:body>
      <w:p><w:r><w:rPr><w:b/></w:rPr><w:t>NGHỊ QUYẾT</w:t></w:r></w:p>
      <w:p><w:r><w:t>Điều 1. </w:t></w:r><w:r><w:rPr><w:i/></w:rPr><w:t>Phạm vi</w:t></w:r></w:p>
      <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Cơ quan</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Hội đồng</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
    </w:body></w:document>"""
    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as docx:
        docx.writestr("word/document.xml", document)
    return archive.getvalue()


def test_converts_docx_paragraphs_inline_formatting_and_tables() -> None:
    markdown = convert_word_to_markdown(_docx_bytes(), "source.docx")

    assert "**NGHỊ QUYẾT**" in markdown
    assert "Điều 1. *Phạm vi*" in markdown
    assert "| Cơ quan | Hội đồng |" in markdown


def test_converts_legacy_doc_using_antiword(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[bytes]:
        observed["command"] = command
        observed["content"] = Path(command[-1]).read_bytes()
        observed["options"] = (check, capture_output, timeout)
        return subprocess.CompletedProcess(command, 0, stdout="Điều 1. Phạm vi.".encode(), stderr=b"")

    monkeypatch.setattr(
        "src.applications.tillegal.ingestion.crawler.parsers.word_to_markdown.subprocess.run",
        fake_run,
    )
    markdown = convert_word_to_markdown(
        bytes.fromhex("D0CF11E0A1B11AE1") + b"word data",
        "source.doc",
        timeout_seconds=12,
    )

    assert markdown == "Điều 1. Phạm vi.\n"
    assert observed["command"][:2] == ["antiword", "-t"]
    assert observed["content"] == bytes.fromhex("D0CF11E0A1B11AE1") + b"word data"
    assert observed["options"] == (False, True, 12)


def test_legacy_doc_reports_missing_antiword(monkeypatch) -> None:
    def missing_antiword(*args, **kwargs):
        raise FileNotFoundError("antiword")

    monkeypatch.setattr(
        "src.applications.tillegal.ingestion.crawler.parsers.word_to_markdown.subprocess.run",
        missing_antiword,
    )

    with pytest.raises(LegacyDocConverterUnavailableError, match="antiword to be installed"):
        convert_word_to_markdown(bytes.fromhex("D0CF11E0A1B11AE1") + b"word data", "source.doc")


def test_rejects_invalid_docx_and_unknown_extensions() -> None:
    with pytest.raises(ValueError, match="DOCX attachment is invalid"):
        convert_word_to_markdown(b"not a zip archive", "source.docx")

    with pytest.raises(ValueError, match="Unsupported"):
        convert_word_to_markdown(b"content", "source.rtf")
