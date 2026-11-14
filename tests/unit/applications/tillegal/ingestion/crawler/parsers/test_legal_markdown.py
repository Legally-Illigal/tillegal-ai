from uuid import UUID

import pytest

from src.applications.tillegal.ingestion.crawler.parsers.legal_markdown import _split_content, parse_legal_markdown

_SOURCE_DOCUMENT_ID = UUID("00000000-0000-0000-0000-000000000001")


def test_chunks_merge_point_blocks_and_include_parent_lead_without_crossing_points() -> None:
    parsed = parse_legal_markdown(
        "**Điều 1. Hệ số**\n\n1. Các hệ số:\n\na) Hệ số gốc:\n\n"
        "Loại I: 3.\n\nLoại II: 2.\n\nb) Hệ số khác.\n\n**Điều 2. Khác**\n\nNội dung.",
        source_document_id=_SOURCE_DOCUMENT_ID, title="Quyết định",
    )
    chunks = [c for c in parsed.chunks if c.node_id == "article-1-clause-1-point-a"]
    assert len(chunks) == 1
    chunk = chunks[0]
    assert "1. Các hệ số:" in chunk.content
    assert "a) Hệ số gốc:\n\nLoại I: 3.\n\nLoại II: 2." in chunk.content
    assert "b)" not in chunk.content
    assert len(chunk.metadata["block_ids"]) == 3
    assert len(chunk.metadata["context_block_ids"]) == 1
    assert chunk.block_id == chunk.metadata["block_ids"][0]
    assert len(parsed.blocks) > len(parsed.chunks)


def test_split_prefers_complete_sentences_and_preserves_all_words() -> None:
    sentences = ["Alpha " + "word " * 8 + ".", "Beta " + "word " * 8 + ".", "Gamma " + "word " * 8 + "."]
    text = " ".join(sentences)
    parts = _split_content("Title > ", text, lambda s: len(s.split()), 24)
    assert parts == [" ".join(sentences[:2]), sentences[2]]
    long_sentence = " ".join(f"word{i}" for i in range(55))
    parts = _split_content("Title > ", long_sentence, lambda s: len(s.split()), 24)
    assert " ".join(parts) == long_sentence
    assert all(len(("Title > " + part).split()) <= 24 for part in parts)
    with pytest.raises(ValueError, match="single word"):
        _split_content("", "x" * 30, len, 24)


def test_appendix_forms_do_not_inherit_main_chapter_or_previous_form_article() -> None:
    markdown = (
        "**Chương VII**\n\n**Điều 21. Hiệu lực**\n\n1. Nội dung.\n\n"
        "**Điều 22. Thi hành**\n\n2. Trách nhiệm.\n\n**PHỤ LỤC**\n\n"
        "1. Mẫu số 1: Danh mục mẫu.\n\nMẫu số 1\n\n**QUYẾT ĐỊNH**\n\n"
        "**Điều 3.** Thi hành mẫu thứ nhất.\n\n**QUYẾT ĐỊNH**\n\n"
        "**Về việc cử Trưởng đoàn**\n\n**QUYẾT ĐỊNH:**\n\n"
        "**Điều 1.** Cử Trưởng đoàn.\n\n**Điều 3.** Thi hành mẫu thứ hai.\n\n"
        "**PHỤ LỤC II**\n\nMẫu số 2\n\n**Chương I**\n\n**Điều 1. Phạm vi**"
    )
    parsed = parse_legal_markdown(markdown, source_document_id=_SOURCE_DOCUMENT_ID, title="Thông tư")
    nodes = {node.node_id: node for node in parsed.nodes}
    assert {node.label for node in parsed.nodes if node.parent_node_id == "chapter-vii"} == {
        "Điều 21: Hiệu lực", "Điều 22: Thi hành",
    }
    assert nodes["appendix-1-attachment-1"].label == "Mẫu số 1"
    target = next(block for block in parsed.blocks if block.content == "Về việc cử Trưởng đoàn")
    assert target.node_id == "appendix-1-attachment-2"
    assert nodes["appendix-1-attachment-2-article-3"].parent_node_id == target.node_id
    chunk = next(chunk for chunk in parsed.chunks if chunk.block_id == target.block_id)
    assert "PHỤ LỤC" in chunk.content and "QUYẾT ĐỊNH" in chunk.content
    assert "Chương VII" not in chunk.content and "Điều 3" not in chunk.content
    assert nodes["appendix-2-attachment-1-chapter-i"].parent_node_id == "appendix-2-attachment-1"
    assert markdown[target.start_offset:target.end_offset] == "**Về việc cử Trưởng đoàn**"


def test_named_appendices_and_form_codes_preserve_scope_across_mastheads() -> None:
    markdown = (
        "**Chương VII**\n\n**Điều 22. Thi hành**\n\n**PHỤ LỤC I. BIỂU MẪU**\n"
        "Mẫu số 01/ABC\n\n| Cơ quan | Quốc hiệu |\n| --- | --- |\n\n"
        "**QUYẾT ĐỊNH**\n\n**Điều 1.** Nội dung mẫu một.\n\n"
        "**PHỤ LỤC II: DANH MỤC**\n\nMẫu số 02/ABC\n\nNội dung mẫu hai."
    )
    parsed = parse_legal_markdown(markdown, source_document_id=_SOURCE_DOCUMENT_ID, title="Thông tư")
    containers = [node for node in parsed.nodes if node.kind in {"appendix", "attachment"}]
    assert [node.label for node in containers] == [
        "PHỤ LỤC I. BIỂU MẪU", "Mẫu số 01/ABC", "PHỤ LỤC II: DANH MỤC", "Mẫu số 02/ABC",
    ]
    article = next(node for node in parsed.nodes if node.node_id.endswith("article-1"))
    assert article.parent_node_id == "appendix-1-attachment-1"
    assert next(b for b in parsed.blocks if b.content == "Nội dung mẫu hai.").node_id == "appendix-2-attachment-1"


def test_wrapped_points_keep_continuations_tables_and_chunk_context() -> None:
    markdown = (
        "**Điều 4. Phân bổ vốn**\n1. Tiêu chí:\na) Nội dung\n"
        "tiếp nối.\n\nHệ số gốc:\n\nXã loại I: 3,0.\n\n"
        "| Loại | Hệ số |\n| --- | --- |\n| I | 3 |\n\n"
        "b) Điểm khác.\n\n2. Khoản tiếp theo.\n\nGiải thích khoản.\n\n"
        "**Điều 5. Thi hành**\n\nNội dung Điều 5."
    )
    parsed = parse_legal_markdown(markdown, source_document_id=_SOURCE_DOCUMENT_ID, title="Nghị quyết")
    wrapped = next(block for block in parsed.blocks if block.content == "a) Nội dung tiếp nối.")
    assert markdown[wrapped.start_offset:wrapped.end_offset] == "a) Nội dung\ntiếp nối."
    for content in ("Hệ số gốc:", "Xã loại I: 3,0."):
        block = next(block for block in parsed.blocks if block.content == content)
        assert block.node_id == "article-4-clause-1-point-a"
        assert any("Điểm a" in chunk.content and content in chunk.content for chunk in parsed.chunks)
    assert next(block for block in parsed.blocks if block.block_type == "table").node_id == wrapped.node_id
    explanation = next(block for block in parsed.blocks if block.content == "Giải thích khoản.")
    assert explanation.node_id == "article-4-clause-2"
    assert next(block for block in parsed.blocks if block.content == "Nội dung Điều 5.").node_id == "article-5"


@pytest.mark.parametrize("marker", ["**", "__"])
@pytest.mark.parametrize("separator", [" ", "\n"])
def test_article_number_only_heading_preserves_searchable_body(marker: str, separator: str) -> None:
    body = "Ban hành kèm theo Quyết định này Quy chế làm việc."
    markdown = f"{marker}Điều 1.{marker}{separator}{body}\nDòng tiếp nối."
    parsed = parse_legal_markdown(markdown, source_document_id=_SOURCE_DOCUMENT_ID, title="Quyết định")
    article = next(node for node in parsed.nodes if node.kind == "article")
    assert article.label == "Điều 1"
    heading, paragraph = parsed.blocks
    assert heading.block_type == "heading"
    assert heading.content == "Điều 1."
    assert paragraph.block_type == "paragraph"
    assert paragraph.content == body + " Dòng tiếp nối."
    assert paragraph.node_id == article.node_id
    assert article.heading_block_id == heading.block_id
    assert markdown[heading.start_offset:heading.end_offset] == f"{marker}Điều 1.{marker}"
    assert markdown[paragraph.start_offset:paragraph.end_offset] == body + "\nDòng tiếp nối."
    assert any(chunk.block_id == paragraph.block_id and body in chunk.content for chunk in parsed.chunks)


@pytest.mark.parametrize("heading", ["**Điều 7. Trách nhiệm**", "**Điều 7.** **Trách nhiệm**"])
def test_full_article_title_remains_a_heading(heading: str) -> None:
    parsed = parse_legal_markdown(
        heading + "\n\n1. Nội dung khoản.", source_document_id=_SOURCE_DOCUMENT_ID, title="Quy chế"
    )
    assert parsed.blocks[0].block_type == "heading"
    assert parsed.blocks[0].content == "Điều 7: Trách nhiệm"
    assert [block.block_type for block in parsed.blocks] == ["heading", "clause"]


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
