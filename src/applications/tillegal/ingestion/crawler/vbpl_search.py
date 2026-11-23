"""Bounded HTTP access to VBPL's issued-date search Server Action."""

import json
import time
from dataclasses import dataclass
from datetime import date

import httpx

from src.core.config import VbplCrawlSettings

SEARCH_URL = "https://vbpl.vn/"


@dataclass(frozen=True)
class SearchPage:
    total: int
    page_number: int
    items: list[dict[str, object]]


def search_payload(start: date, end: date, page: int, size: int = 10) -> list[dict[str, object]]:
    if start > end or page < 1 or not 1 <= size <= 50:
        raise ValueError("Invalid issued-date range or pagination")
    return [
        {
            "pageNumber": page,
            "pageSize": size,
            "sortBy": "issueDate",
            "sortDirection": "desc",
            "groupVbpl": True,
            "issueDateFrom": f"{start.isoformat()}T00:00:00",
            "issueDateTo": f"{end.isoformat()}T23:59:59.999",
            "optionDoc": "all",
            "matchMode": "all_words",
        }
    ]


def parse_search_response(body: str, start: date, end: date, page: int, size: int = 10) -> SearchPage:
    # Flight record 0 references the action result; other records can contain UI data.
    records = {}
    for line in body.splitlines():
        key, separator, value = line.partition(":")
        if separator:
            try:
                records[key] = json.loads(value)
            except json.JSONDecodeError:
                continue
    root = records.get("0")
    reference = root[0] if isinstance(root, list) and root else None
    if not isinstance(reference, str) or not reference.startswith("$@"):
        raise ValueError("Unrecognized VBPL action response; verify Next-Action configuration")
    result = records.get(reference[2:])
    if not isinstance(result, dict) or not isinstance(result.get("items"), list):
        raise ValueError("VBPL action returned no search result")
    total = result.get("total")
    items = result["items"]
    if type(total) is not int or total < 0 or result.get("pageNumber") != page:
        raise ValueError("Invalid VBPL total or page number")
    if result.get("pageSize") != size or len(items) > size:
        raise ValueError("VBPL changed page size")
    if len(items) != min(size, max(0, total - (page - 1) * size)):
        raise ValueError("VBPL returned an incomplete page")
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Invalid VBPL item")
        record_id = item.get("id")
        if not isinstance(record_id, str) or not record_id or record_id in seen:
            raise ValueError("Missing or duplicate VBPL record ID")
        seen.add(record_id)
        issued = date.fromisoformat(str(item.get("issueDate", ""))[:10])
        if not start <= issued <= end:
            raise ValueError("VBPL returned a document outside the requested issued-date range")
        url = item.get("document_url")
        if url != f"https://vbpl.vn/van-ban/chi-tiet/{record_id}":
            raise ValueError("Unexpected VBPL document URL")
    return SearchPage(total, page, items)


def fetch_search_page(start: date, end: date, page: int, settings: VbplCrawlSettings) -> SearchPage:
    payload = search_payload(start, end, page)
    headers = {
        "Accept": "text/x-component",
        "Content-Type": "text/plain;charset=UTF-8",
        "Next-Action": settings.search_action_id,
        "Origin": SEARCH_URL.rstrip("/"),
        "Referer": SEARCH_URL,
        "User-Agent": "Tillegal-VBPL-Crawler/0.1",
    }
    started = time.monotonic()
    with httpx.Client(timeout=min(45, settings.page_timeout_seconds), follow_redirects=False) as client:
        with client.stream("POST", SEARCH_URL, headers=headers, content=json.dumps(payload)) as response:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_bytes(65536):
                if time.monotonic() - started > 90:
                    raise TimeoutError("VBPL search exceeded time limit")
                content.extend(chunk)
                if len(content) > settings.max_page_size_mb * 1024 * 1024:
                    raise ValueError("VBPL search response exceeds configured size limit")
    return parse_search_response(content.decode("utf-8"), start, end, page)
