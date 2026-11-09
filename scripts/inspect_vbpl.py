"""Capture VBPL pages and summarize their HTML metadata for source research."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from email.message import Message
from html.parser import HTMLParser
from http.client import HTTPResponse
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_RESPONSE_BYTES = 5 * 1024 * 1024
USER_AGENT = "Tillegal-VBPL-Research/0.1"


class PageInventory(HTMLParser):
    """Extract useful page structure without interpreting page content."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title_parts: list[str] = []
        self.title_depth = 0
        self.metadata: dict[str, list[str]] = {}
        self.links: list[str] = []
        self.scripts: list[str] = []
        self.forms: list[dict[str, object]] = []
        self._current_form: dict[str, object] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): value for key, value in attrs if value is not None}
        if tag == "title":
            self.title_depth += 1
        elif tag == "meta":
            key = (
                attributes.get("name")
                or attributes.get("property")
                or attributes.get("itemprop")
                or attributes.get("http-equiv")
            )
            value = attributes.get("content")
            if key and value:
                self.metadata.setdefault(key, []).append(value)
        elif tag == "a" and attributes.get("href"):
            self.links.append(urljoin(self.base_url, attributes["href"]))
        elif tag == "script" and attributes.get("src"):
            self.scripts.append(urljoin(self.base_url, attributes["src"]))
        elif tag == "form":
            self._current_form = {
                "action": urljoin(self.base_url, attributes.get("action", "")),
                "method": attributes.get("method", "get").lower(),
                "fields": [],
            }
        elif tag in {"input", "select", "textarea", "button"} and self._current_form is not None:
            name = attributes.get("name")
            if name:
                fields = self._current_form["fields"]
                if isinstance(fields, list):
                    fields.append({"name": name, "type": attributes.get("type", tag)})

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self.title_depth:
            self.title_depth -= 1
        elif tag == "form" and self._current_form is not None:
            self.forms.append(self._current_form)
            self._current_form = None

    def handle_data(self, data: str) -> None:
        if self.title_depth:
            self.title_parts.append(data)

    def result(self) -> dict[str, object]:
        return {
            "title": " ".join(" ".join(self.title_parts).split()),
            "metadata": self.metadata,
            "links": list(dict.fromkeys(self.links)),
            "scripts": list(dict.fromkeys(self.scripts)),
            "forms": self.forms,
        }


def _is_vbpl_url(url: str) -> bool:
    parsed = urlsplit(url)
    hostname = (parsed.hostname or "").lower()
    return (
        parsed.scheme == "https"
        and (hostname == "vbpl.vn" or hostname.endswith(".vbpl.vn"))
        and parsed.username is None
        and parsed.password is None
    )


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
        if not _is_vbpl_url(new_url):
            raise ValueError(f"Refusing redirect outside vbpl.vn: {new_url}")
        return super().redirect_request(request, file_pointer, code, message, headers, new_url)


def _capture_page(url: str, output_dir: Path, index: int) -> dict[str, object]:
    if not _is_vbpl_url(url):
        raise ValueError(f"Only HTTPS URLs on vbpl.vn are allowed: {url}")

    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    opener = build_opener(_VbplRedirectHandler())
    with opener.open(request, timeout=30) as response:
        final_url = response.geturl()
        if not _is_vbpl_url(final_url):
            raise ValueError(f"Refusing final URL outside vbpl.vn: {final_url}")
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type.lower():
            raise ValueError(f"Expected HTML from {url}, received {content_type or 'unknown content type'}")
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError(f"HTML response exceeds {MAX_RESPONSE_BYTES} bytes: {url}")

        charset = response.headers.get_content_charset() or "utf-8"
        html = body.decode(charset, errors="replace")
        inventory = PageInventory(final_url)
        inventory.feed(html)

        digest = hashlib.sha256(body).hexdigest()
        html_name = f"{index:03d}-{digest[:12]}.html"
        (output_dir / html_name).write_bytes(body)
        return {
            "requested_url": url,
            "final_url": final_url,
            "status": response.status,
            "content_type": content_type,
            "last_modified": response.headers.get("Last-Modified"),
            "etag": response.headers.get("ETag"),
            "bytes": len(body),
            "sha256": digest,
            "html_file": html_name,
            **inventory.result(),
        }


def inspect_pages(urls: list[str], output_dir: Path) -> tuple[Path, list[dict[str, object]]]:
    """Save each page's raw HTML and a JSON inventory; report failures per URL."""
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for index, url in enumerate(urls, start=1):
        if index > 1:
            time.sleep(1)
        try:
            records.append(_capture_page(url, output_dir, index))
        except (OSError, URLError, TimeoutError, ValueError) as error:
            records.append({"requested_url": url, "error": f"{type(error).__name__}: {error}"})

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "captured_at": datetime.now(UTC).isoformat(),
                "user_agent": USER_AGENT,
                "pages": records,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest_path, records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urls", nargs="+", help="HTTPS page URLs hosted on vbpl.vn")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/vbpl-inspection"),
        help="Directory for raw HTML captures and manifest.json",
    )
    args = parser.parse_args(argv)

    manifest_path, records = inspect_pages(args.urls, args.output)
    for record in records:
        if "error" in record:
            print(f"ERROR {record['requested_url']}: {record['error']}", file=sys.stderr)
        else:
            print(
                f"OK {record['status']} {record['final_url']} "
                f"title={ascii(record['title'])} bytes={record['bytes']}"
            )
    print(f"Manifest: {manifest_path}")
    return int(any("error" in record for record in records))


if __name__ == "__main__":
    raise SystemExit(main())
