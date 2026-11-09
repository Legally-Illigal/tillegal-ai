"""Tests for the read-only VBPL page inspection utility."""

import pytest

from scripts.inspect_vbpl import PageInventory, _is_vbpl_url


def test_page_inventory_extracts_page_metadata_and_routes() -> None:
    parser = PageInventory("https://vbpl.vn/")
    parser.feed(
        """
        <html>
          <head>
            <title> Cơ sở dữ liệu pháp luật </title>
            <meta name="dateModified" content="2026-11-09">
            <script src="/assets/app.js"></script>
          </head>
          <body>
            <a href="/van-ban?id=1">Văn bản</a>
            <form action="/search" method="POST">
              <input name="documentNumber" type="text">
            </form>
          </body>
        </html>
        """
    )

    assert parser.result() == {
        "title": "Cơ sở dữ liệu pháp luật",
        "metadata": {"dateModified": ["2026-11-09"]},
        "links": ["https://vbpl.vn/van-ban?id=1"],
        "scripts": ["https://vbpl.vn/assets/app.js"],
        "forms": [
            {
                "action": "https://vbpl.vn/search",
                "method": "post",
                "fields": [{"name": "documentNumber", "type": "text"}],
            }
        ],
    }


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://vbpl.vn/", True),
        ("https://data.vbpl.vn/document/1", True),
        ("http://vbpl.vn/", False),
        ("https://vbpl.vn.example.com/", False),
        ("https://example.com/", False),
        ("https://user:password@vbpl.vn/", False),
    ],
)
def test_vbpl_url_validation(url: str, expected: bool) -> None:
    assert _is_vbpl_url(url) is expected
