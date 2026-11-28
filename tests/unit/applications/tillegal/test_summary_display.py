from copy import deepcopy

from src.applications.tillegal.agents.response.renderer import render_display_response, source_location


def test_sources_and_readable_limits_without_mutation():
    value = {
        "answer_draft": "Nội dung minh họa. [R1]",
        "status": "DRAFT_UNVERIFIED",
        "citations": [
            {
                "citation_id": "R1",
                "title": "Văn bản minh họa",
                "source_url": "https://example.org",
                "chunk_metadata": {"breadcrumb": "Văn bản minh họa > Chương I > Điều 5: Tiêu đề > Khoản 2 > Điểm a"},
            }
        ],
        "limitations": [
            "DRAFT_NOT_VERIFIED",
            "JUDGE_INSUFFICIENT",
            "TEMPORAL_METADATA_INCOMPLETE",
            "I:abc123: Thiếu thông tin về thủ tục.",
            "E:abc123:APPLICABILITY_AT_AS_OF_DATE_NOT_VERIFIED",
        ],
    }
    before = deepcopy(value)
    text = render_display_response(value)
    assert value == before
    assert "[R1] Văn bản minh họa — Điều 5; Khoản 2; Điểm a." in text
    assert "Thiếu thông tin về thủ tục." in text
    assert "https://" not in text and "I:abc" not in text and "DRAFT_NOT_VERIFIED" not in text
    assert "Chưa xác minh đầy đủ hiệu lực" in text


def test_no_inference_from_references_in_body():
    citation = {"content": "Theo Điều 10 TCVN 9385:2012", "chunk_metadata": {}}
    assert source_location(citation) == []
    citation["chunk_metadata"] = {"breadcrumb": "Văn bản > Điều 5 > Khoản 2"}
    assert source_location(citation) == ["Điều 5", "Khoản 2"]


def test_hyphen_scope_and_duplicate_procedure_gaps():
    value = {
        "status": "DRAFT_UNVERIFIED",
        "answer_draft": "Bản nháp.",
        "issue_reports": [{"issue_id": "I:abc123"}],
        "limitations": [
            "Thiếu quy định chi tiết về thủ tục hoặc các bước cụ thể khi lắp đặt bổ sung "
            "hệ thống chống sét cho nhà ở hiện hữu tại Cần Thơ.",
            "I:abc123: Chưa đủ căn cứ để trả lời toàn bộ vấn đề.",
            "issue_id: I:abc123 - Chưa có thông tin chi tiết về trình tự, thủ tục hoặc các bước cụ thể "
            "khi thực hiện việc lắp đặt bổ sung hệ thống chống sét cho nhà ở hiện hữu tại Cần Thơ.",
        ],
    }
    before = deepcopy(value)
    text = render_display_response(value)
    assert "issue_id" not in text and "I:abc123" not in text
    assert text.count("thủ tục") == 1 and "Chưa đủ căn cứ để trả lời toàn bộ" not in text
    assert value == before


def test_distinct_issues_and_gaps_are_preserved():
    from src.applications.tillegal.agents.response.renderer import readable_limitations

    value = {
        "limitations": [
            "issue_id: I:abc - Thiếu thủ tục cấp phép.",
            "issue_id: I:def — Thiếu thủ tục cấp phép.",
            "I:abc: Thiếu căn cứ về ngoại lệ.",
        ]
    }
    assert "Thiếu căn cứ về ngoại lệ." in readable_limitations(value)
    assert all("I:" not in s for s in readable_limitations(value))
