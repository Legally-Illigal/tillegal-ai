import pytest

from src.applications.tillegal.ingestion.crawler.parsers.html_to_markdown import (
    clean_legal_markdown,
    convert_html_to_markdown,
)


def test_cleanup_removes_multiline_administrative_tables_but_preserves_attachment() -> None:
    markdown = (
        "| HỘI ĐỒNG NHÂN DÂN\nTỈNH A | CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
        "Độc lập - Tự do - Hạnh phúc |\n| --- | --- |\n| Số: 1/2026 | Ngày 1 |\n\n"
        "**QUYẾT ĐỊNH**\n\nCăn cứ Luật A;\n\n**Điều 1.** Ban hành quy định.\n\n"
        "| ***Nơi nhận:***\n- Cơ quan A; | **CHỦ TỊCH**<br>Nguyễn Văn A |\n| --- | --- |\n\n"
        "**QUY ĐỊNH**\n\n(Ban hành kèm theo Quyết định số 1/2026)\n\n"
        "**Điều 1. Phạm vi**\n\n1. Nội dung quy định.\n"
    )
    cleaned = clean_legal_markdown(markdown)
    assert cleaned.startswith("**QUYẾT ĐỊNH**")
    assert "Nơi nhận" not in cleaned
    assert "Nguyễn Văn A" not in cleaned
    assert "CỘNG HÒA" not in cleaned
    assert "**QUY ĐỊNH**" in cleaned
    assert "(Ban hành kèm theo Quyết định số 1/2026)" in cleaned
    assert "**Điều 1.** Ban hành quy định." in cleaned
    assert cleaned.endswith("1. Nội dung quy định.\n")
    assert clean_legal_markdown(cleaned) == cleaned


def test_cleanup_preserves_substantive_tables_and_mentions_of_officials() -> None:
    markdown = (
        "**Điều 1. Trách nhiệm**\n\nChủ tịch có trách nhiệm thông báo nơi nhận.\n\n"
        "| Mức phí | Số tiền |\n| --- | --- |\n| A | 100 |\n"
    )
    assert clean_legal_markdown(markdown) == markdown


def test_cleanup_removes_empty_tables_and_standalone_signature_resumes_at_appendix() -> None:
    markdown = (
        "**QUYẾT ĐỊNH**\n\n| | |\n| --- | --- |\n\n"
        "**ỦY BAN NHÂN DÂN TỈNH A**\n\nCăn cứ Luật A;\n\n"
        "**Điều 1.** Nội dung.\n\n**KT. CHỦ TỊCH**\n\n**PHÓ CHỦ TỊCH**\n\n"
        "Nguyễn Văn A\n\n**PHỤ LỤC I**\n\n| Hạng | Giá |\n| --- | --- |\n| A | 10 |\n"
    )
    cleaned = clean_legal_markdown(markdown)
    assert "ỦY BAN NHÂN DÂN TỈNH A" not in cleaned
    assert "KT. CHỦ TỊCH" not in cleaned
    assert "Nguyễn Văn A" not in cleaned
    assert "| | |" not in cleaned
    assert "Căn cứ Luật A;" in cleaned
    assert "**PHỤ LỤC I**" in cleaned
    assert "| A | 10 |" in cleaned


def test_cleanup_does_not_trim_articles_before_an_attachment_title() -> None:
    markdown = (
        "Số: 1/2026\n\n**Quyết định về việc ban hành quy chế**\n\n"
        "**Điều 1.** Ban hành quy chế.\n\n**QUY CHẾ**\n\n**Điều 1.** Phạm vi.\n"
    )
    assert clean_legal_markdown(markdown) == markdown


def test_converts_vbpl_document_body_to_markdown() -> None:
    html = """
    <!doctype html>
    <html>
      <head><title>Ignored title</title><style>body { display: none; }</style></head>
      <body>
        <table><tr><td><p><strong>HỘI ĐỒNG NHÂN DÂN</strong></p></td>
        <td><p align="right"><em>Hà Nội, ngày 1 tháng 1</em></p></td></tr></table>
        <p align="center"><strong>NGHỊ QUYẾT</strong></p>
        <p>Điều 1. <strong>Phạm vi</strong> điều chỉnh &amp; đối tượng.</p>
        <ol><li>Thứ nhất</li><li>Thứ hai</li></ol>
      </body>
    </html>
    """

    markdown = convert_html_to_markdown(html)

    assert "| **HỘI ĐỒNG NHÂN DÂN** | *Hà Nội, ngày 1 tháng 1* |" in markdown
    assert "##" not in markdown
    assert "**NGHỊ QUYẾT**" in markdown
    assert "Điều 1. **Phạm vi** điều chỉnh & đối tượng." in markdown
    assert "1. Thứ nhất\n2. Thứ hai" in markdown
    assert "Ignored title" not in markdown
    assert "display: none" not in markdown


def test_converts_html_breaks_and_escapes_table_pipes() -> None:
    markdown = convert_html_to_markdown("<table><tr><td>A|B<br>C</td></tr></table>")

    assert "| A\\|B<br>C |" in markdown


def test_keeps_word_boundaries_between_formatted_inline_elements() -> None:
    markdown = convert_html_to_markdown("<p><em>one</em><strong>two</strong>three</p>")

    assert "*one* **two** three" in markdown


def test_rejects_empty_or_non_utf8_body_html() -> None:
    with pytest.raises(ValueError, match="empty Markdown"):
        convert_html_to_markdown("<html><body><p> &nbsp; </p></body></html>")

    with pytest.raises(UnicodeDecodeError):
        convert_html_to_markdown(b"<html><body>\xff</body></html>")
