"""Synthetic contracts only. No human labels, model weights or external calls required."""
import hashlib
import json
from math import log2
from threading import Lock

import pytest

pytest.importorskip("ai_core")
from ai_core.data_contracts import content_hash
from ai_core.rag_generation import GenerationError
from scripts.evaluate_frozen_retrieval import binary_ndcg
from scripts.score_answer_reviews import score
from src.applications.tillegal.graphs.semantic import assess, finish, generate_claims


class Fixture:
    mode = "fixture"
    model = "unit-test"

    def __init__(self, result):
        self.result = result

    def generate(self, messages):
        return json.dumps(self.result)


QUOTE = "Hồ sơ được giữ 12 ngày."
ROW = {"evidence_id": "id", "quote": QUOTE, "quote_sha256":content_hash(QUOTE),
       "document_version_id":"v1", "chunk_id":"c"}
CLAIM = {"claim_id":"C1", "text":"Thời gian lưu là mười hai ngày.", "evidence_id":"id"}


def state():
    return {"question":"Lưu bao lâu?", "plan":{"clarification":None}, "judgments":[{"selected":["id"]}],
            "proposals":[CLAIM], "evidence":{"id":ROW}, "workflow":"semantic", "search_trace":[],
            "bundles":[], "usage":{}}


@pytest.mark.parametrize("verdict,span,expected", [
    ("SUPPORTED", "12 ngày", "SUPPORTED"), ("CONTRADICTED", "12 ngày", "CONTRADICTED"),
    ("INSUFFICIENT_EVIDENCE", "", "INSUFFICIENT_EVIDENCE"), ("SUPPORTED", "15 ngày","NOT_EVALUATED"),
    ("SUPPORTED", "", "NOT_EVALUATED"), ("invalid", "12 ngày", "NOT_EVALUATED")])
def test_claim_span_contract(verdict, span, expected):
    provider = Fixture({"verdict":verdict, "span":span, "reason":"Synthetic fixture."})
    check = assess(CLAIM, {"id":ROW}, provider, Lock())
    assert check["claim_support"] == expected and check["claim_id"] == "C1"
    assert check["temporal_applicability"] == "NOT_EVALUATED" and check["source_reachability"] == "NOT_CHECKED"
    assert check["trace"]["document_version_id"] == "v1"
    if check["evidence_span"]:
        coords = check["evidence_span"]
        assert QUOTE[coords["start"]:coords["end"]] == coords["text"]


def test_generation_maps_alias_and_rejects_forged_id():
    for ref in ("E1", "foreign"):
        provider = Fixture({"claims":[{"text":CLAIM["text"], "evidence_id":ref}]})
        if ref == "E1":
            assert generate_claims(state(), provider, Lock())["proposals"] == [CLAIM]
        else:
            with pytest.raises(GenerationError, match="INVALID_OUTPUT"):
                generate_claims(state(), provider, Lock())


def test_claim_chapeau_cannot_be_published_even_when_source_is_complete():
    claim = dict(CLAIM, text="Hồ sơ có thời hạn như sau:")
    provider = Fixture({"verdict":"SUPPORTED", "span":QUOTE, "reason":"Synthetic overly permissive judge."})
    s = state()
    s["proposals"] = [claim]
    result = finish(s, provider, provider, Lock())["output"]
    assert result["status"] == "ABSTAINED"
    assert result["citation_checks"][0]["publication_blocker"] == "LIST_REQUIRES_FOLLOWING_ITEMS"


def test_invented_number_is_blocked_despite_supported_model_verdict():
    s = state()
    s["proposals"] = [dict(CLAIM, text="Hồ sơ được giữ 99 ngày.")]
    provider = Fixture({"verdict":"SUPPORTED", "span":QUOTE, "reason":"Synthetic false positive."})
    result = finish(s, provider, provider, Lock())["output"]
    assert result["status"] == "ABSTAINED"
    assert result["citation_checks"][0]["publication_blocker"] == "UNSOURCED_NUMERIC_VALUE"


def test_article_title_cannot_support_entitlement_but_clause_can():
    title = "Điều 1. Bảo hiểm xã hội"
    row = dict(ROW, quote=title, quote_sha256=content_hash(title), is_heading=True)
    provider = Fixture({"verdict":"SUPPORTED", "span":title, "reason":"Synthetic permissive title match."})
    assert assess(CLAIM, {"id":row}, provider, Lock())["publication_blocker"] == "TITLE_IS_NOT_CLAIM_EVIDENCE"
    # EvidenceBuilder may flag a substantive clause as a heading for its children.
    clause = "1. Hồ sơ được giữ 12 ngày."
    row = dict(row, quote=clause, quote_sha256=content_hash(clause))
    assert assess(CLAIM, {"id":row}, None, Lock())["publication_blocker"] is None


def test_context_titles_remain_visible_but_are_not_citable():
    s = state()
    s["context_selection"] = {"version":"context-v2"}
    title = "Điều 1. Lưu hồ sơ"
    s["evidence"]["title"] = dict(ROW, quote=title, is_heading=True)
    s["judgments"] = [{"selected":["title", "id"]}]
    class Inspect(Fixture):
        def generate(self, messages):
            payload = json.loads(messages[-1]["content"])
            assert payload["sources"] == {"E1":QUOTE}
            assert payload["context_headings_not_citable"] == [title]
            return super().generate(messages)
    result = generate_claims(s, Inspect({"claims":[{"text":QUOTE, "evidence_id":"E1"}]}), Lock())
    assert result["proposals"][0]["evidence_id"] == "id"


def test_numeric_guard_accepts_equivalent_leading_zero_not_invented_value():
    quote = "Hồ sơ được giữ ít nhất 01 ngày."
    row = dict(ROW, quote=quote, quote_sha256=content_hash(quote))
    claim = dict(CLAIM, text="Hồ sơ được giữ ít nhất 1 ngày.")
    assert assess(claim, {"id":row}, None, Lock())["publication_blocker"] is None
    claim["text"] = "Hồ sơ được giữ 1 ngày."
    assert assess(claim, {"id":row}, None, Lock())["publication_blocker"] == "NUMERIC_BOUND_REQUIRES_REVIEW"


def test_explicit_when_condition_cannot_disappear_from_claim():
    quote = "3. Khi nghỉ hằng năm, người lao động được tạm ứng tiền lương."
    row = dict(ROW, quote=quote, quote_sha256=content_hash(quote))
    claim = dict(CLAIM, text="Người lao động được tạm ứng tiền lương.")
    assert assess(claim, {"id":row}, None, Lock())["publication_blocker"] == "CONDITION_REQUIRES_REVIEW"
    claim["text"] = "Trong thời gian nghỉ hằng năm người lao động được tạm ứng tiền lương."
    assert assess(claim, {"id":row}, None, Lock())["publication_blocker"] is None


def test_recurring_year_condition_cannot_be_replaced_by_months():
    quote = "Cứ đủ 05 năm làm việc cho một người sử dụng lao động thì số ngày nghỉ được tăng thêm 01 ngày."
    row = dict(ROW, quote=quote, quote_sha256=content_hash(quote))
    claim = dict(CLAIM, text="Tôi được nghỉ 1 ngày khi làm việc ba tháng.")
    assert assess(claim, {"id":row}, None, Lock())["publication_blocker"] == "CONDITION_REQUIRES_REVIEW"
    claim["text"] = "Cứ đủ 5 năm làm việc cho một người sử dụng lao động thì số ngày nghỉ được tăng thêm 1 ngày."
    assert assess(claim, {"id":row}, None, Lock())["publication_blocker"] is None


def test_fail_closed_integrity_and_semantic_filter():
    s = state()
    provider = Fixture({"verdict":"CONTRADICTED","span":QUOTE,"reason":"mismatch"})
    assert finish(s, provider, provider, Lock())["output"]["status"] == "ABSTAINED"
    assert finish(s, provider, None, Lock())["output"]["status"] == "ABSTAINED"
    s["workflow"] = "draft"
    assert finish(s, provider, None, Lock())["output"]["claims"] == [CLAIM]
    s["evidence"] = {"id":dict(ROW,quote="altered")}
    assert not finish(s, provider, None, Lock())["output"]["claims"]


def test_ndcg_cutoff_and_unresolved_slots():
    assert binary_ndcg(["x","a","b"], {"a","b"}, 2) == pytest.approx((1/log2(3))/(1+1/log2(3)))
    assert binary_ndcg([], {"a"}, 5) == 0


def test_review_bound_to_report_and_complete(tmp_path):
    p = tmp_path/"case.json"
    p.write_text(json.dumps({"rows":[{"case":"X","mode":"draft","answer":"Example","status":"DRAFT"}]}))
    annotation = {"reviewer_id":"synthetic-test-only","reviewer_type":"human",
                  "report_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
                  "answers":[{"case":"X","mode":"draft","relevant":True,"all_material_claims_reviewed":True,
                              "claims":[{"text":"Example","verdict":"INSUFFICIENT_EVIDENCE","citations_correct":False}]}]}
    assert score(p,annotation)["draft"]["unsupported_claim_rate"] == 1
    annotation["answers"] = []
    with pytest.raises(ValueError):
        score(p,annotation)

def test_supported_intro_or_unfilled_template_cannot_be_published():
    for quote in ("Các trường hợp sau:", "Ngày nghỉ:........"):
        s = state()
        s["evidence"]["id"] = dict(ROW,quote=quote,quote_sha256=content_hash(quote))
        provider = Fixture({"verdict":"SUPPORTED","span":quote,"reason":"synthetic positive verdict"})
        result = finish(s,provider,provider,Lock())["output"]
        assert result["citation_checks"][0]["claim_support"] == "SUPPORTED"
        assert result["citation_checks"][0]["publication_blocker"]
        assert result["status"] == "ABSTAINED"


@pytest.mark.parametrize("quote,claim,blocked", [
    ("Ít nhất phải bằng 85% mức lương.", "Tiền lương phải bằng 85%.", True),
    ("Ít nhất phải bằng 85% mức lương.", "Mức trả thấp nhất trong thời gian thử việc là 85%.", False),
    ("Thời hạn không quá 30 ngày.", "Thời hạn tối thiểu là 30 ngày.", True),
    ("Thời hạn không quá 30 ngày.", "Thời hạn tối đa là 30 ngày.", False),
])
def test_numeric_bound_publication_guard(quote,claim,blocked):
    source = dict(ROW, quote=quote, quote_sha256=content_hash(quote))
    provider = Fixture({"verdict":"SUPPORTED","span":quote,"reason":"model verdict in test"})
    result = assess(dict(CLAIM,text=claim),{"id":source},provider,Lock())
    assert (result["publication_blocker"] == "NUMERIC_BOUND_REQUIRES_REVIEW") == blocked
