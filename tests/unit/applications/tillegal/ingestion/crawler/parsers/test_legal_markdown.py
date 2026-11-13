from uuid import UUID

import pytest

from src.applications.tillegal.ingestion.crawler.parsers.legal_markdown import parse_legal_markdown

_SOURCE_DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.parametrize("marker", ["đ", "Đ"])
def test_point_d_stroke_has_distinct_id_and_correct_order(marker: str) -> None:
    parsed = parse_legal_markdown(
        f"Điều 1. Trách nhiệm\n\n1. Nhiệm vụ:\n\nd) Nội dung d\n\n{marker}) Nội dung đ\n\ne) Nội dung e",
        source_document_id=_SOURCE_DOCUMENT_ID,
        title="Quy chế",
    )
    points = [node for node in parsed.nodes if node.kind == "point"]
    assert [node.node_id for node in points] == [f"article-1-clause-1-point-{suffix}" for suffix in ("d", "dd", "e")]
    assert [node.label for node in points] == ["Điểm d", "Điểm đ", "Điểm e"]
    assert [node.ordinal for node in points] == [3, 4, 5]
    point_dd = points[1]
    assert point_dd.parent_node_id == "article-1-clause-1"
    assert any(block.node_id == point_dd.node_id and block.content == "đ) Nội dung đ" for block in parsed.blocks)
    assert any(chunk.node_id == point_dd.node_id and "Điểm đ" in chunk.content for chunk in parsed.chunks)


def test_parses_legal_hierarchy_and_builds_breadcrumb_chunks() -> None:
    markdown = """# NGHỊ ĐỊNH

## Chương I. QUY ĐỊNH CHUNG

### Điều 1. Phạm vi điều chỉnh

1. Nghị định này quy định về hồ sơ điện tử.

a) Áp dụng đối với cơ quan nhà nước.

## Chương II. TIẾP NHẬN HỒ SƠ

### Điều 2. Thời hạn

2. Cơ quan tiếp nhận xử lý hồ sơ trong thời hạn quy định.
"""

    parsed = parse_legal_markdown(
        markdown,
        source_document_id=_SOURCE_DOCUMENT_ID,
        title="Nghị định số 25/2026/NĐ-CP",
    )
    nodes = {node.node_id: node for node in parsed.nodes}
    chunks = [chunk.content for chunk in parsed.chunks]

    assert nodes["chapter-i"].kind == "chapter"
    assert nodes["chapter-i-article-1"].parent_node_id == "chapter-i"
    assert nodes["chapter-i-article-1-clause-1"].parent_node_id == "chapter-i-article-1"
    assert nodes["chapter-i-article-1-clause-1-point-a"].parent_node_id == "chapter-i-article-1-clause-1"
    assert any(
        chunk.startswith(
            "Nghị định số 25/2026/NĐ-CP > Chương I. QUY ĐỊNH CHUNG > Điều 1: Phạm vi điều chỉnh > Khoản 1 > "
        )
        for chunk in chunks
    )
    assert any("> Khoản 1 > Điểm a > a) Áp dụng" in chunk for chunk in chunks)
    assert all(chunk.content_sha256 for chunk in parsed.chunks)
    assert parsed.structure.content_sha256


def test_splits_long_block_to_fit_configured_token_limit() -> None:
    markdown = "## Chương I. QUY ĐỊNH CHUNG\n\n### Điều 1. Phạm vi\n\n1. " + " ".join(f"từ{i}" for i in range(60))

    def count_tokens(value: str) -> int:
        return len(value.split())

    parsed = parse_legal_markdown(
        markdown,
        source_document_id=_SOURCE_DOCUMENT_ID,
        title="Nghị định",
        token_counter=count_tokens,
        max_chunk_tokens=32,
    )

    assert len(parsed.chunks) > 1
    assert all(count_tokens(chunk.content) <= 32 for chunk in parsed.chunks)
    assert all(chunk.block_id is not None for chunk in parsed.chunks)


def test_reports_when_no_article_heading_is_detected() -> None:
    parsed = parse_legal_markdown(
        "Một nội dung chưa có heading điều.",
        source_document_id=_SOURCE_DOCUMENT_ID,
        title="Văn bản",
    )

    assert parsed.structure.issues == [{"code": "no_articles_detected", "message": "No Điều headings were recognized."}]
