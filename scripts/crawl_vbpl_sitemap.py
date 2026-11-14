"""Select VBPL document pages whose official sitemap lastmod matches a date."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.applications.tillegal.ingestion.crawler.vbpl_sitemap import (
    SITEMAP_INDEX_URL,
    SitemapFetchError,
    current_vietnam_date,
    scan_vbpl_sitemaps,
)


def _target_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD format") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date",
        type=_target_date,
        default=current_vietnam_date(),
        help="VBPL sitemap lastmod date to select (default: today in Asia/Ho_Chi_Minh)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/vbpl-sitemap"),
        help="Directory for the scan result JSON",
    )
    args = parser.parse_args(argv)

    try:
        result = scan_vbpl_sitemaps(args.date)
    except SitemapFetchError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    args.output.mkdir(parents=True, exist_ok=True)
    output_path = args.output / f"sitemap-scan-{args.date.isoformat()}.json"
    output_path.write_text(
        json.dumps(
            {
                "scanned_at": datetime.now(ZoneInfo("UTC")).isoformat(),
                "source": SITEMAP_INDEX_URL,
                "target_date": result.target_date.isoformat(),
                "sitemap_count": result.sitemap_count,
                "document_url_count": result.document_url_count,
                "selected_count": len(result.selected),
                "shards": [
                    {
                        "url": shard.url,
                        "document_url_count": shard.document_url_count,
                        "selected_count": shard.selected_count,
                    }
                    for shard in result.shards
                ],
                "selected": [
                    {
                        "url": document.url,
                        "sitemap_lastmod": document.lastmod.isoformat(),
                        "sitemap_url": document.sitemap_url,
                    }
                    for document in result.selected
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Scanned {result.sitemap_count} sitemaps and {result.document_url_count} document URLs; "
        f"selected {len(result.selected)} for {args.date.isoformat()}."
    )
    print(f"Results: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
