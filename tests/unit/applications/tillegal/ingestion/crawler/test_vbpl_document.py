import json
from datetime import date

import httpx
import pytest

from src.applications.tillegal.ingestion.crawler.vbpl_document import (
    VbplAttachment,
    VbplDocumentFetchError,
    _attachment_download_url,
    _attribute_date,
    _find_file_list_action,
    _parse_action_attachments,
    _parse_document_attributes,
    _parse_metadata,
    _read_document_page,
    _read_page_head,
    parse_document_id,
)


def test_document_attributes_are_read_from_matching_initial_doc_across_chunks() -> None:
    document = {
        "id": "175384", "issueDate": "2026-10-22T00:00:00",
        "effFrom": "2026-11-01T00:00:00", "effTo": None,
        "effStatus": {"code": "CHL", "name": "Còn hiệu lực"},
    }
    payload = json.dumps({"initialDoc": document}, ensure_ascii=False)
    html = '<head><title>Document</title></head><body>'
    for part in (payload[:35], payload[35:]):
        html += f'<script>self.__next_f.push({json.dumps([1, part])})</script>'
    response = httpx.Response(200, text=html + '</body>')
    attributes = _parse_document_attributes(_read_document_page(response, 10000), "175384")
    assert _attribute_date(attributes, "issueDate") == date(2026, 10, 22)
    assert _attribute_date(attributes, "effFrom") == date(2026, 11, 1)
    assert _attribute_date(attributes, "effTo") is None
    assert attributes["effStatus"] == document["effStatus"]


@pytest.mark.parametrize("document", [{"id": "other", "issueDate": "2026-10-22"}, None])
def test_document_attributes_reject_missing_or_wrong_document(document) -> None:
    payload = json.dumps([1, json.dumps({"initialDoc": document})])
    with pytest.raises(VbplDocumentFetchError, match="requested document"):
        _parse_document_attributes(f'<script>self.__next_f.push({payload})</script>', "175384")


@pytest.mark.parametrize("value", ["2026-02-30", "unknown", 20261022])
def test_attribute_date_rejects_invalid_source_values(value) -> None:
    with pytest.raises(VbplDocumentFetchError, match="invalid effTo"):
        _attribute_date({"effTo": value}, "effTo")


def test_attribute_date_preserves_expiry_and_missing_dates() -> None:
    assert _attribute_date({"effTo": "2027-01-01T00:00:00"}, "effTo") == date(2027, 1, 1)
    assert _attribute_date({"effTo": ""}, "effTo") is None
    assert _attribute_date({}, "effTo") is None


def test_read_document_page_enforces_body_size_limit() -> None:
    with pytest.raises(VbplDocumentFetchError, match="page exceeds"):
        _read_document_page(httpx.Response(200, content=b'<head></head>' + b'x' * 100), 50)


def test_parse_document_id_from_vbpl_detail_url() -> None:
    assert parse_document_id("https://vbpl.vn/van-ban/chi-tiet/nghi-quyet--175384?tabs=hien-thi-pdf") == "175384"


def test_parse_document_id_from_vbpl_uuid_detail_url() -> None:
    record_id = "233cd180-dbe8-11f1-a612-37d3797320a3"
    url = f"https://vbpl.vn/van-ban/chi-tiet/nghi-quyet--{record_id}"

    assert parse_document_id(url) == record_id


def test_parse_document_id_normalizes_uuid_case() -> None:
    url = "https://vbpl.vn/van-ban/chi-tiet/nghi-quyet--233CD180-DBE8-11F1-A612-37D3797320A3"

    assert parse_document_id(url) == "233cd180-dbe8-11f1-a612-37d3797320a3"


def test_parse_document_id_rejects_non_vbpl_host() -> None:
    with pytest.raises(VbplDocumentFetchError, match="outside"):
        parse_document_id("https://example.com/van-ban/chi-tiet/document--175384")


def test_parse_document_id_rejects_unsupported_record_id() -> None:
    with pytest.raises(VbplDocumentFetchError, match="numeric ID or UUID"):
        parse_document_id("https://vbpl.vn/van-ban/chi-tiet/document--not-an-id")


def test_parse_metadata_collects_title_meta_and_json_ld() -> None:
    title, metadata = _parse_metadata(
        '<html><head><meta property="og:title" content="Nghị quyết">'
        '<script type="application/ld+json">{"@type":"Legislation"}</script></head></html>'
    )

    assert title == "Nghị quyết"
    assert metadata["meta_tags"] == {"og:title": "Nghị quyết"}
    assert metadata["json_ld"] == [{"@type": "Legislation"}]


def test_read_page_head_ignores_large_document_body() -> None:
    html = (
        b"<html><head><title>Resolution</title>"
        b'<script src="/_next/static/chunks/page.js"></script></head><body>' + b"x" * (5 * 1024 * 1024 + 1)
    )
    response = httpx.Response(200, content=html)

    page_head = _read_page_head(response)

    assert page_head.endswith("</head>")
    assert "page.js" in page_head
    assert len(page_head.encode()) < 1024


def test_read_page_head_rejects_an_oversized_head(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.applications.tillegal.ingestion.crawler.vbpl_document.MAX_PAGE_BYTES",
        16,
    )
    response = httpx.Response(200, content=b"<head>" + b"x" * 17)

    with pytest.raises(VbplDocumentFetchError, match="page head exceeds"):
        _read_page_head(response)


def test_find_file_list_action_from_public_bundle() -> None:
    action_id = "7b29f485c8e43b71a94bfc11b54459d7e27293e6"
    bundle = f'n.d(e,{{ny:function(){{return o}}}});n(67500);var r=n(65949),o=(0,r.$)("{action_id}")'
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=bundle))

    with httpx.Client(transport=transport) as client:
        found = _find_file_list_action(
            client,
            '<html><script src="/_next/static/chunks/files.js"></script></html>',
            "https://vbpl.vn/van-ban/chi-tiet/document--175384",
        )

    assert found == action_id


def test_parse_action_attachments_returns_metadata_without_signed_url() -> None:
    response = (
        '0:["$@1",["build",null]]\n'
        '1:[{"id":null,"fileName":"source.pdf","fullPath":"175384/source.pdf",'
        '"type":"application/octet-stream","size":120,'
        '"presignedUrl":"https://s3-han02.fptcloud.com/source.pdf?signature=temporary"}]\n'
        '</html>3:[{"id":null,"fileName":"body_content.html","relatedType":"BODY_CONTENT"}]'
    )

    attachments = _parse_action_attachments(response)

    assert len(attachments) == 2
    assert attachments[0].file_name == "source.pdf"
    assert attachments[0].full_path == "175384/source.pdf"
    assert attachments[0].size == 120
    assert attachments[0].presigned_url == "https://s3-han02.fptcloud.com/source.pdf?signature=temporary"
    assert attachments[1].file_name == "body_content.html"
    assert attachments[1].full_path is None
    assert attachments[1].size is None
    assert attachments[1].presigned_url is None


def test_attachment_download_uses_vbpl_presigned_url_for_unicode_filename() -> None:
    attachment = VbplAttachment(
        "VanBanGoc_BẢNG GIÁ ĐẤT.pdf",
        "175384/VanBanGoc_BẢNG GIÁ ĐẤT.pdf",
        "application/pdf",
        120,
        "https://s3-han02.fptcloud.com/object?signature=temporary",
    )

    assert _attachment_download_url("175384", attachment) == "https://s3-han02.fptcloud.com/object?signature=temporary"


def test_attachment_download_rejects_untrusted_presigned_url() -> None:
    attachment = VbplAttachment(
        "source.pdf",
        "175384/source.pdf",
        "application/pdf",
        120,
        "https://example.com/object?signature=temporary",
    )

    with pytest.raises(VbplDocumentFetchError, match="unsupported signed download URL"):
        _attachment_download_url("175384", attachment)


def test_pdf_header_may_follow_binary_prefix() -> None:
    from src.applications.tillegal.ingestion.crawler.vbpl_document import _PDF_HEADER

    content = b"\x75\xab\x5a\x01\xaa" + b"\x00" * 16 + b"%PDF-1.3\n"

    assert _PDF_HEADER.search(content[:1024]) is not None


def test_pdf_header_outside_first_1024_bytes_is_not_accepted() -> None:
    from src.applications.tillegal.ingestion.crawler.vbpl_document import _PDF_HEADER

    content = b"\x00" * 1024 + b"%PDF-1.3\n"

    assert _PDF_HEADER.search(content[:1024]) is None


def test_parse_action_attachments_accepts_an_explicit_empty_list() -> None:
    assert _parse_action_attachments('0:["$@1",["build",null]]\n1:[]') == ()


def test_parse_action_attachments_rejects_an_unrecognized_response() -> None:
    with pytest.raises(VbplDocumentFetchError, match="recognizable"):
        _parse_action_attachments("1:E{}")
