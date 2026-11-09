"""Tests for VBPL sitemap discovery and date filtering."""

from datetime import date

import pytest

from src.applications.tillegal.ingestion.crawler.vbpl_sitemap import (
    SITEMAP_INDEX_URL,
    SitemapFetchError,
    parse_document_sitemap,
    parse_sitemap_index,
    scan_vbpl_sitemaps,
)


def test_parse_sitemap_index_returns_vbpl_children() -> None:
    xml = b"""<?xml version="1.0"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap><loc>https://vbpl.vn/sitemap/1.xml</loc></sitemap>
      <sitemap><loc>https://vbpl.vn/sitemap/2.xml</loc></sitemap>
    </sitemapindex>"""

    assert parse_sitemap_index(xml) == (
        "https://vbpl.vn/sitemap/1.xml",
        "https://vbpl.vn/sitemap/2.xml",
    )


@pytest.mark.parametrize(
    "location",
    [
        "http://vbpl.vn/sitemap/1.xml",
        "https://vbpl.vn.example.com/sitemap/1.xml",
        "https://example.com/sitemap/1.xml",
    ],
)
def test_parse_sitemap_index_rejects_non_vbpl_locations(location: str) -> None:
    xml = (
        '<sitemapindex><sitemap><loc>'
        f"{location}"
        "</loc></sitemap></sitemapindex>"
    ).encode()

    with pytest.raises(SitemapFetchError, match="outside https://vbpl.vn"):
        parse_sitemap_index(xml)


def test_parse_document_sitemap_selects_only_document_urls_for_date() -> None:
    xml = b"""<?xml version="1.0"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url>
        <loc>https://vbpl.vn/van-ban/chi-tiet/doc-a</loc>
        <lastmod>2026-11-09</lastmod>
      </url>
      <url>
        <loc>https://vbpl.vn/van-ban/chi-tiet/doc-b</loc>
        <lastmod>2026-11-08T23:59:59Z</lastmod>
      </url>
      <url>
        <loc>https://vbpl.vn/van-ban/trung-uong</loc>
        <lastmod>2026-11-09</lastmod>
      </url>
    </urlset>"""

    count, selected = parse_document_sitemap(
        xml,
        "https://vbpl.vn/sitemap/1.xml",
        date(2026, 11, 9),
    )

    assert count == 2
    assert [(item.url, item.lastmod) for item in selected] == [
        ("https://vbpl.vn/van-ban/chi-tiet/doc-a", date(2026, 11, 9))
    ]


def test_scan_reads_all_sitemaps_and_deduplicates_selected_urls() -> None:
    index = b"""<sitemapindex>
      <sitemap><loc>https://vbpl.vn/sitemap/0.xml</loc></sitemap>
      <sitemap><loc>https://vbpl.vn/sitemap/1.xml</loc></sitemap>
    </sitemapindex>"""
    static = b"""<urlset>
      <url><loc>https://vbpl.vn/</loc><lastmod>2026-11-09</lastmod></url>
    </urlset>"""
    documents = b"""<urlset>
      <url><loc>https://vbpl.vn/van-ban/chi-tiet/doc-a</loc><lastmod>2026-11-09</lastmod></url>
      <url><loc>https://vbpl.vn/van-ban/chi-tiet/doc-b</loc><lastmod>2026-11-08</lastmod></url>
    </urlset>"""
    responses = {
        SITEMAP_INDEX_URL: index,
        "https://vbpl.vn/sitemap/0.xml": static,
        "https://vbpl.vn/sitemap/1.xml": documents,
    }

    result = scan_vbpl_sitemaps(
        date(2026, 11, 9),
        request_pause_seconds=0,
        fetch=responses.__getitem__,
    )

    assert result.sitemap_count == 2
    assert result.document_url_count == 2
    assert [item.url for item in result.selected] == [
        "https://vbpl.vn/van-ban/chi-tiet/doc-a"
    ]


def test_scan_surfaces_missing_child_sitemap_response() -> None:
    def fetch(url: str) -> bytes:
        if url == SITEMAP_INDEX_URL:
            return b"<sitemapindex><sitemap><loc>https://vbpl.vn/sitemap/1.xml</loc></sitemap></sitemapindex>"
        raise SitemapFetchError("network unavailable")

    with pytest.raises(SitemapFetchError, match="network unavailable"):
        scan_vbpl_sitemaps(date(2026, 11, 9), request_pause_seconds=0, fetch=fetch)
