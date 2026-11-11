import pytest

from src.applications.tillegal.ingestion.crawler.parsers.html_to_markdown import convert_html_to_markdown


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
