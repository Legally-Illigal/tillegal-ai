"""Fetch VBPL document metadata and source files through the public website APIs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlsplit
from uuid import UUID

import httpx

from src.core.config import VbplCrawlSettings

VBPL_HOST = "vbpl.vn"
VBPL_GATEWAY_HOST = "vbpl-bientap-gateway.moj.gov.vn"
USER_AGENT = "Tillegal-VBPL-Crawler/0.1"
MAX_PAGE_BYTES = 5 * 1024 * 1024
MAX_BUNDLE_BYTES = 5 * 1024 * 1024
MAX_ATTACHMENT_BYTES = 100 * 1024 * 1024
PAGE_READ_CHUNK_BYTES = 64 * 1024
FILE_LIST_PARTS = [1, 2, 4]
_HEAD_END_TAG = re.compile(rb"</head\s*>", re.IGNORECASE)
_PDF_HEADER = re.compile(rb"%PDF-\d\.\d")
_ACTION_EXPORT = re.compile(r"ny\s*:\s*function\s*\(\)\s*\{\s*return\s+([\w$]+)\s*\}")
_ACTION_REFERENCE = re.compile(r"\b([\w$]+)\s*=\s*\(0,\s*[\w$]+\.\$\)\s*\(\s*\"([a-f0-9]{40})\"\s*\)")
_DOCUMENT_ID = re.compile(r"--([^/]+)$")
_FILE_LIST_ACTION_ID: str | None = None


class VbplDocumentFetchError(RuntimeError):
    """Raised when VBPL metadata or source files cannot be fetched safely."""


@dataclass(frozen=True)
class VbplAttachment:
    """Metadata for a file exposed by a VBPL document page."""

    file_name: str
    full_path: str | None
    content_type: str
    size: int | None
    presigned_url: str | None = None


@dataclass(frozen=True)
class VbplDocumentPage:
    """Rendered-source metadata needed to ingest one VBPL document."""

    document_id: str
    title: str
    metadata: dict[str, object]
    attachments: tuple[VbplAttachment, ...]
    issued_on: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    effect_status_reported: str | None = None
    document_number: str | None = None
    document_type: str | None = None
    issuing_authority: str | None = None


class _PageMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.json_ld: list[object] = []
        self.title = ""
        self._in_title = False
        self._in_json_ld = False
        self._script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value for key, value in attrs if value is not None}
        if tag.lower() == "meta":
            key = attributes.get("property") or attributes.get("name")
            value = attributes.get("content")
            if key and value:
                self.meta[key] = value.strip()
        elif tag.lower() == "title":
            self._in_title = True
        elif tag.lower() == "script" and attributes.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self._script_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
        elif tag.lower() == "script" and self._in_json_ld:
            value = "".join(self._script_parts).strip()
            if value:
                try:
                    self.json_ld.append(json.loads(value))
                except json.JSONDecodeError:
                    self.json_ld.append({"raw": value})
            self._in_json_ld = False
            self._script_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_json_ld:
            self._script_parts.append(data)


def parse_document_id(document_url: str) -> str:
    parsed = urlsplit(document_url)
    if parsed.scheme != "https" or parsed.hostname != VBPL_HOST or parsed.username or parsed.password:
        raise VbplDocumentFetchError(f"Refusing VBPL URL outside https://{VBPL_HOST}: {document_url}")
    match = _DOCUMENT_ID.search(parsed.path.rstrip("/"))
    if match is None:
        raise VbplDocumentFetchError(f"VBPL document URL has no supported record ID: {document_url}")
    record_id = match.group(1)
    if record_id.isdecimal():
        return record_id
    try:
        return str(UUID(record_id))
    except ValueError as error:
        raise VbplDocumentFetchError(f"VBPL document URL must end with a numeric ID or UUID: {document_url}") from error


def _parse_metadata(html: str) -> tuple[str, dict[str, object]]:
    parser = _PageMetadataParser()
    parser.feed(html)
    title = parser.meta.get("og:title") or parser.meta.get("twitter:title") or parser.title.strip()
    if not title:
        raise VbplDocumentFetchError("VBPL document page did not expose a title")
    return title, {
        "meta_tags": parser.meta,
        "json_ld": parser.json_ld,
    }


def _read_page_head(response: httpx.Response, max_page_bytes: int | None = None) -> str:
    """Read only the bounded HTML head needed for metadata and script discovery."""
    if max_page_bytes is None:
        max_page_bytes = MAX_PAGE_BYTES
    head = bytearray()
    for chunk in response.iter_bytes(chunk_size=PAGE_READ_CHUNK_BYTES):
        head.extend(chunk)
        match = _HEAD_END_TAG.search(head)
        if match is not None:
            return bytes(head[: match.end()]).decode(response.encoding or "utf-8", errors="replace")
        if len(head) > max_page_bytes:
            raise VbplDocumentFetchError(f"VBPL document page head exceeds {max_page_bytes} bytes")
    raise VbplDocumentFetchError("VBPL document page did not contain a closing </head> tag")


def _read_document_page(response: httpx.Response, max_page_bytes: int) -> str:
    """Read the bounded page, including document attributes in Next.js hydration data."""
    content = bytearray()
    for chunk in response.iter_bytes(chunk_size=PAGE_READ_CHUNK_BYTES):
        content.extend(chunk)
        if len(content) > max_page_bytes:
            raise VbplDocumentFetchError(f"VBPL document page exceeds {max_page_bytes} bytes")
    return content.decode(response.encoding or "utf-8", errors="replace")


def _parse_document_attributes(html: str, document_id: str) -> dict[str, object]:
    """Extract only the requested initialDoc, never related documents or UI labels."""
    parts: list[str] = []
    for match in re.finditer(r"self\.__next_f\.push\((.*?)\)</script>", html, re.DOTALL):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list) and len(payload) == 2 and payload[0] == 1 and isinstance(payload[1], str):
            parts.append(payload[1])
    data = "".join(parts)
    decoder = json.JSONDecoder()
    for match in re.finditer(r'"initialDoc"\s*:\s*', data):
        try:
            document, _ = decoder.raw_decode(data, match.end())
        except json.JSONDecodeError:
            continue
        if isinstance(document, dict) and str(document.get("id")) == document_id:
            return {
                key: document.get(key)
                for key in ("issueDate", "effFrom", "effTo", "effStatus", "docNum", "docType", "agencyName")
            }
    raise VbplDocumentFetchError("VBPL page did not expose attributes for the requested document")


def _attribute_date(attributes: dict[str, object], key: str) -> date | None:
    value = attributes.get(key)
    if value is None or value == "":
        return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            pass
    raise VbplDocumentFetchError(f"VBPL document has an invalid {key}: {value!r}")


def _attribute_text(attributes: dict[str, object], key: str, *, named: bool = False) -> str | None:
    value = attributes.get(key)
    if value is None:
        return None
    if named:
        if not isinstance(value, dict):
            raise VbplDocumentFetchError(f"VBPL document has an invalid {key}")
        value = value.get("name")
    if value is None:
        return None
    if not isinstance(value, str):
        raise VbplDocumentFetchError(f"VBPL document has an invalid {key}")
    return value.strip() or None


def _script_urls(html: str, page_url: str) -> tuple[str, ...]:
    sources = re.findall(r"""<script\b[^>]*\bsrc=["']([^"']+\.js(?:\?[^"']*)?)["']""", html, re.IGNORECASE)
    urls: list[str] = []
    for source in sources:
        url = urljoin(page_url, source)
        parsed = urlsplit(url)
        if parsed.scheme == "https" and parsed.hostname == VBPL_HOST:
            urls.append(url)
    return tuple(dict.fromkeys(urls))


def _find_file_list_action(
    client: httpx.Client,
    html: str,
    page_url: str,
    max_bundle_bytes: int | None = None,
) -> str:
    if max_bundle_bytes is None:
        max_bundle_bytes = MAX_BUNDLE_BYTES
    for script_url in _script_urls(html, page_url):
        response = client.get(script_url)
        if response.status_code != 200:
            continue
        if len(response.content) > max_bundle_bytes:
            continue
        source = response.text
        export_match = _ACTION_EXPORT.search(source)
        if export_match is None:
            continue
        action_variable = re.escape(export_match.group(1))
        tail = source[export_match.end() : export_match.end() + 5000]
        for reference in _ACTION_REFERENCE.finditer(tail):
            if reference.group(1) == export_match.group(1):
                return reference.group(2)
        variable_reference = re.search(
            rf"\b{action_variable}\s*=\s*\(0,\s*[\w$]+\.\$\)\s*\(\s*\"([a-f0-9]{{40}})\"\s*\)",
            tail,
        )
        if variable_reference is not None:
            return variable_reference.group(1)
    raise VbplDocumentFetchError("Could not locate VBPL's public document-file listing action")


def _parse_action_attachments(body: str) -> tuple[VbplAttachment, ...]:
    attachments: list[VbplAttachment] = []
    seen_names: set[str] = set()
    decoder = json.JSONDecoder()
    for match in re.finditer(r'"fileName"\s*:', body):
        object_start = body.rfind("{", 0, match.start())
        if object_start < 0:
            continue
        try:
            item, _ = decoder.raw_decode(body, object_start)
        except json.JSONDecodeError as error:
            raise VbplDocumentFetchError("VBPL file-list action returned invalid attachment JSON") from error
        if not isinstance(item, dict) or not isinstance(item.get("fileName"), str):
            continue
        file_name = item.get("fileName")
        full_path = item.get("fullPath")
        content_type = item.get("type")
        size = item.get("size")
        presigned_url = item.get("presignedUrl")
        if not file_name or file_name in seen_names:
            continue
        if full_path is not None and not isinstance(full_path, str):
            raise VbplDocumentFetchError(f"VBPL attachment has an invalid path: {file_name}")
        if content_type is not None and not isinstance(content_type, str):
            raise VbplDocumentFetchError(f"VBPL attachment has an invalid content type: {file_name}")
        if size is not None and (not isinstance(size, int) or size < 0):
            raise VbplDocumentFetchError(f"VBPL attachment has invalid type or size: {file_name}")
        if presigned_url is not None and not isinstance(presigned_url, str):
            raise VbplDocumentFetchError(f"VBPL attachment has an invalid download URL: {file_name}")
        attachments.append(
            VbplAttachment(
                file_name,
                full_path,
                content_type or "application/octet-stream",
                size,
                presigned_url,
            )
        )
        seen_names.add(file_name)
    if not attachments and re.search(r"(?:^|[\n>])\d+:\[\s*\]", body) is None:
        raise VbplDocumentFetchError("VBPL file-list action returned no recognizable attachment data")
    return tuple(attachments)


def fetch_vbpl_document_page(
    document_url: str,
    settings: VbplCrawlSettings | None = None,
) -> VbplDocumentPage:
    """Fetch document metadata and list attachments through the public Next.js action."""
    global _FILE_LIST_ACTION_ID

    document_id = parse_document_id(document_url)
    max_page_bytes = settings.max_page_size_mb * 1024 * 1024 if settings else MAX_PAGE_BYTES
    max_bundle_bytes = settings.max_bundle_size_mb * 1024 * 1024 if settings else MAX_BUNDLE_BYTES
    page_timeout_seconds = settings.page_timeout_seconds if settings else 45
    with httpx.Client(
        timeout=httpx.Timeout(page_timeout_seconds),
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
    ) as client:
        with client.stream("GET", document_url) as response:
            if response.status_code != 200:
                raise VbplDocumentFetchError(f"VBPL detail page returned HTTP {response.status_code}: {document_url}")
            page_head = _read_document_page(response, max_page_bytes)
        title, metadata = _parse_metadata(page_head)
        attributes = _parse_document_attributes(page_head, document_id)
        metadata["document_attributes"] = attributes
        issued_on = _attribute_date(attributes, "issueDate")
        effective_from = _attribute_date(attributes, "effFrom")
        effective_to = _attribute_date(attributes, "effTo")
        status = attributes.get("effStatus")
        status_name = status.get("name") if isinstance(status, dict) else None
        if status_name is not None and not isinstance(status_name, str):
            raise VbplDocumentFetchError("VBPL document has an invalid effect status name")
        action_id = _FILE_LIST_ACTION_ID or _find_file_list_action(
            client,
            page_head,
            document_url,
            max_bundle_bytes,
        )
        # Keep the site's anti-bot cookies, but avoid carrying its locale preference into this action.
        for cookie in tuple(client.cookies.jar):
            if cookie.name == "NEXT_LOCALE":
                client.cookies.jar.clear(cookie.domain, cookie.path, cookie.name)
        try:
            attachments = _request_attachments(
                client,
                document_url,
                document_id,
                action_id,
                max_page_bytes,
            )
        except VbplDocumentFetchError:
            if _FILE_LIST_ACTION_ID is None:
                raise
            action_id = _find_file_list_action(client, page_head, document_url, max_bundle_bytes)
            attachments = _request_attachments(
                client,
                document_url,
                document_id,
                action_id,
                max_page_bytes,
            )
        _FILE_LIST_ACTION_ID = action_id

    return VbplDocumentPage(
        document_id, title, metadata, attachments,
        issued_on, effective_from, effective_to, status_name,
        document_number=_attribute_text(attributes, "docNum"),
        document_type=_attribute_text(attributes, "docType", named=True),
        issuing_authority=_attribute_text(attributes, "agencyName"),
    )


def _request_attachments(
    client: httpx.Client,
    document_url: str,
    document_id: str,
    action_id: str,
    max_page_bytes: int | None = None,
) -> tuple[VbplAttachment, ...]:
    if max_page_bytes is None:
        max_page_bytes = MAX_PAGE_BYTES
    action_response = client.post(
        document_url,
        headers={
            "Next-Action": action_id,
            "Accept": "text/x-component",
            "Content-Type": "text/plain;charset=UTF-8",
        },
        content=json.dumps([document_id, FILE_LIST_PARTS], separators=(",", ":")),
    )
    if action_response.status_code != 200:
        raise VbplDocumentFetchError(
            f"VBPL file-list action returned HTTP {action_response.status_code}: {document_url}"
        )
    if len(action_response.content) > max_page_bytes:
        raise VbplDocumentFetchError("VBPL file-list response exceeded the size limit")
    return _parse_action_attachments(action_response.text)


def download_vbpl_attachment(
    document_id: str,
    attachment: VbplAttachment,
    settings: VbplCrawlSettings | None = None,
) -> bytes:
    """Download one listed attachment from VBPL's public gateway."""
    url = _attachment_download_url(document_id, attachment)
    max_attachment_bytes = settings.max_attachment_size_mb * 1024 * 1024 if settings else MAX_ATTACHMENT_BYTES
    timeout_seconds = settings.attachment_timeout_seconds if settings else 90
    with httpx.Client(
        timeout=httpx.Timeout(timeout_seconds),
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream,*/*;q=0.8"},
    ) as client:
        response = client.get(url)
    if response.status_code != 200:
        raise VbplDocumentFetchError(
            f"VBPL attachment download returned HTTP {response.status_code}: {attachment.file_name}"
        )
    if len(response.content) > max_attachment_bytes:
        raise VbplDocumentFetchError(f"VBPL attachment exceeds {max_attachment_bytes} bytes: {attachment.file_name}")
    if attachment.size is not None and attachment.size and len(response.content) != attachment.size:
        raise VbplDocumentFetchError(
            f"VBPL attachment size mismatch for {attachment.file_name}: "
            f"expected {attachment.size}, received {len(response.content)}"
        )
    if attachment.file_name.lower().endswith(".pdf") and _PDF_HEADER.search(response.content[:1024]) is None:
        raise VbplDocumentFetchError(f"VBPL attachment is not a valid PDF: {attachment.file_name}")
    if attachment.file_name.lower().endswith(".html") and b"<!doctype html" not in response.content[:512].lower():
        raise VbplDocumentFetchError(f"VBPL attachment is not a valid HTML document: {attachment.file_name}")
    return response.content


def _attachment_download_url(document_id: str, attachment: VbplAttachment) -> str:
    if attachment.presigned_url is not None:
        parsed_url = urlsplit(attachment.presigned_url)
        hostname = parsed_url.hostname or ""
        if (
            parsed_url.scheme != "https"
            or parsed_url.username is not None
            or parsed_url.password is not None
            or parsed_url.fragment
            or not (hostname == "fptcloud.com" or hostname.endswith(".fptcloud.com"))
        ):
            raise VbplDocumentFetchError(
                f"VBPL attachment has an unsupported signed download URL: {attachment.file_name}"
            )
        return attachment.presigned_url

    return (
        f"https://{VBPL_GATEWAY_HOST}/api/qtdc/public/doc/minio/buckets/vbpl/"
        f"{quote(document_id, safe='')}/{quote(attachment.file_name, safe='')}/download"
    )
