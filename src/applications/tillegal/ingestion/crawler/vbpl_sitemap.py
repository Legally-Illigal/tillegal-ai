"""Discover VBPL document pages through the public sitemap index."""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from email.message import Message
from http.client import HTTPResponse
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zoneinfo import ZoneInfo

SITEMAP_INDEX_URL = "https://vbpl.vn/sitemap.xml"
USER_AGENT = "Tillegal-VBPL-Crawler/0.1"
MAX_SITEMAP_BYTES = 10 * 1024 * 1024
MAX_SITEMAP_COUNT = 100
DOCUMENT_PATH_PREFIX = "/van-ban/chi-tiet/"
VIETNAM_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


class SitemapFetchError(RuntimeError):
    """Raised when a sitemap cannot be safely fetched or parsed."""


@dataclass(frozen=True)
class VbplDocumentUrl:
    url: str
    lastmod: date
    sitemap_url: str


@dataclass(frozen=True)
class SitemapShardResult:
    url: str
    document_url_count: int
    selected_count: int


@dataclass(frozen=True)
class SitemapScanResult:
    target_date: date
    sitemap_count: int
    document_url_count: int
    selected: tuple[VbplDocumentUrl, ...]
    shards: tuple[SitemapShardResult, ...]


def current_vietnam_date() -> date:
    """Return today's date in the timezone used by VBPL's displayed dates."""
    return datetime.now(VIETNAM_TIMEZONE).date()


def _validate_vbpl_url(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "vbpl.vn"
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise SitemapFetchError(f"Refusing URL outside https://vbpl.vn: {url}")


class _VbplRedirectHandler(HTTPRedirectHandler):
    def redirect_request(
        self,
        request: Request,
        file_pointer: HTTPResponse,
        code: int,
        message: str,
        headers: Message,
        new_url: str,
    ) -> Request | None:
        _validate_vbpl_url(new_url)
        return super().redirect_request(request, file_pointer, code, message, headers, new_url)


def _fetch_sitemap(url: str) -> bytes:
    _validate_vbpl_url(url)
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/xml, text/xml;q=0.9, */*;q=0.1",
        },
    )
    try:
        with build_opener(_VbplRedirectHandler()).open(request, timeout=45) as response:
            _validate_vbpl_url(response.geturl())
            body = response.read(MAX_SITEMAP_BYTES + 1)
    except (OSError, URLError, TimeoutError, ValueError) as error:
        raise SitemapFetchError(f"Failed to fetch sitemap {url}: {error}") from error

    if len(body) > MAX_SITEMAP_BYTES:
        raise SitemapFetchError(f"Sitemap exceeds {MAX_SITEMAP_BYTES} bytes: {url}")
    return body


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]


def _child_text(element: ET.Element, child_name: str) -> str | None:
    for child in element:
        if _local_name(child.tag) == child_name and child.text:
            return child.text.strip()
    return None


def _parse_xml(xml_bytes: bytes, source_url: str) -> ET.Element:
    try:
        return ET.fromstring(xml_bytes)
    except ET.ParseError as error:
        raise SitemapFetchError(f"Invalid XML in sitemap {source_url}: {error}") from error


def parse_sitemap_index(xml_bytes: bytes) -> tuple[str, ...]:
    """Parse and validate child sitemap locations from the public index."""
    root = _parse_xml(xml_bytes, SITEMAP_INDEX_URL)
    if _local_name(root.tag) != "sitemapindex":
        raise SitemapFetchError("VBPL sitemap index did not contain a sitemapindex document")

    locations: list[str] = []
    for child in root:
        if _local_name(child.tag) != "sitemap":
            continue
        location = _child_text(child, "loc")
        if location is None:
            raise SitemapFetchError("VBPL sitemap index contains an entry without a location")
        _validate_vbpl_url(location)
        locations.append(location)

    if not locations:
        raise SitemapFetchError("VBPL sitemap index contains no child sitemaps")
    if len(locations) > MAX_SITEMAP_COUNT:
        raise SitemapFetchError(f"VBPL sitemap index exceeds the {MAX_SITEMAP_COUNT}-sitemap limit")
    if len(set(locations)) != len(locations):
        raise SitemapFetchError("VBPL sitemap index contains duplicate child sitemap locations")
    return tuple(locations)


def _parse_lastmod(value: str, source_url: str) -> date:
    try:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError as error:
        raise SitemapFetchError(f"Invalid lastmod date {value!r} in sitemap {source_url}") from error


def parse_document_sitemap(
    xml_bytes: bytes,
    sitemap_url: str,
    target_date: date,
) -> tuple[int, tuple[VbplDocumentUrl, ...]]:
    """Return the document URL count and entries with lastmod equal to target_date."""
    _validate_vbpl_url(sitemap_url)
    root = _parse_xml(xml_bytes, sitemap_url)
    if _local_name(root.tag) != "urlset":
        raise SitemapFetchError(f"Child sitemap is not a urlset: {sitemap_url}")

    document_url_count = 0
    selected: list[VbplDocumentUrl] = []
    for child in root:
        if _local_name(child.tag) != "url":
            continue
        location = _child_text(child, "loc")
        if location is None:
            raise SitemapFetchError(f"Sitemap entry has no location: {sitemap_url}")
        _validate_vbpl_url(location)
        if urlsplit(location).path.startswith(DOCUMENT_PATH_PREFIX):
            document_url_count += 1
            lastmod_value = _child_text(child, "lastmod")
            if lastmod_value is None:
                continue
            lastmod = _parse_lastmod(lastmod_value, sitemap_url)
            if lastmod == target_date:
                selected.append(VbplDocumentUrl(location, lastmod, sitemap_url))

    return document_url_count, tuple(selected)


def scan_vbpl_sitemaps(
    target_date: date,
    *,
    request_pause_seconds: float = 0.25,
    fetch: Callable[[str], bytes] | None = None,
) -> SitemapScanResult:
    """Read every public sitemap and select document URLs lastmodded on target_date."""
    if request_pause_seconds < 0:
        raise ValueError("request_pause_seconds must be non-negative")
    fetch_sitemap = fetch or _fetch_sitemap
    sitemap_urls = parse_sitemap_index(fetch_sitemap(SITEMAP_INDEX_URL))

    document_url_count = 0
    selected_by_url: dict[str, VbplDocumentUrl] = {}
    shards: list[SitemapShardResult] = []
    for index, sitemap_url in enumerate(sitemap_urls):
        if index:
            time.sleep(request_pause_seconds)
        shard_count, shard_selected = parse_document_sitemap(
            fetch_sitemap(sitemap_url),
            sitemap_url,
            target_date,
        )
        document_url_count += shard_count
        shards.append(SitemapShardResult(sitemap_url, shard_count, len(shard_selected)))
        for document in shard_selected:
            existing = selected_by_url.get(document.url)
            if existing is None or document.lastmod > existing.lastmod:
                selected_by_url[document.url] = document

    selected = tuple(
        sorted(
            selected_by_url.values(),
            key=lambda item: (item.lastmod, item.url),
        )
    )
    return SitemapScanResult(
        target_date=target_date,
        sitemap_count=len(sitemap_urls),
        document_url_count=document_url_count,
        selected=selected,
        shards=tuple(shards),
    )
