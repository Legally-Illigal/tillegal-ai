"""Search contract, failure detection and resume behavior."""

import json
from datetime import date

import pytest

from src.applications.tillegal.ingestion.crawler.vbpl_search import parse_search_response, search_payload

START = date(2024, 1, 1)
END = date(2024, 1, 31)


def response(items=None, total=1, page=1):
    if items is None:
        items = [
            {"id": "123", "issueDate": "2024-01-31T00:00:00", "document_url": "https://vbpl.vn/van-ban/chi-tiet/123"}
        ]
    return (
        '0:["$@a",[]]\n'
        + "a:"
        + json.dumps(
            {
                "items": items,
                "total": total,
                "pageNumber": page,
                "pageSize": 10,
            }
        )
    )


def test_payload_uses_issue_dates_not_lastmod():
    payload = search_payload(START, END, 2)[0]
    assert payload["issueDateFrom"] == "2024-01-01T00:00:00"
    assert payload["issueDateTo"] == "2024-01-31T23:59:59.999"
    assert payload["pageNumber"] == 2
    assert "lastmod" not in payload
    with pytest.raises(ValueError):
        search_payload(END, START, 1)


def test_flight_reference_and_empty_results():
    assert parse_search_response(response(), START, END, 1).items[0]["id"] == "123"
    assert parse_search_response(response([], 0), START, END, 1).total == 0


@pytest.mark.parametrize(
    "body",
    [
        "<html>blocked</html>",
        '0:["$@1"]\n1:{"error":"action expired"}',
        response([], 100),
        response(page=2),
        response().replace("2024-01-31", "2024-02-01"),
        response().replace("https://vbpl.vn/", "https://example.com/"),
    ],
)
def test_invalid_or_incomplete_responses_fail_closed(body):
    with pytest.raises(ValueError):
        parse_search_response(body, START, END, 1)
