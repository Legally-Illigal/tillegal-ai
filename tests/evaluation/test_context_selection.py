"""Context selection adversarial fixtures, never legal gold."""

import asyncio
import copy
from hashlib import sha256

import pytest

pytest.importorskip("ai_core")
from src.applications.tillegal.agents.judge.agent import judge
from src.applications.tillegal.agents.judge.context_selection import context_judge, select_context
from src.applications.tillegal.agents.query.agent import understand
from src.framework.tools.error_handling import ToolExecutionError


def row(key, text, *, version="v1", heading=False, scope="main", node="body", ancestors=None):
    return {
        "evidence_id": key,
        "quote": text,
        "quote_sha256": sha256(text.encode()).hexdigest(),
        "document_version_id": version,
        "document_id": "doc",
        "chunk_id": key,
        "article_id": "article",
        "attachment_status": "STRUCTURAL",
        "is_heading": heading,
        "chunk": {
            "scope": scope,
            "node_id": node,
            "ancestor_ids": ancestors or ["article"],
            "issues": [],
            "document_version_id": version,
            "text": text,
            "text_sha256": sha256(text.encode()).hexdigest(),
        },
        "document": {"document_version_id": version},
        "ancestry": [{"node_id": "article", "kind": "article"}],
        "source_locator": {"block_source_start": int(key[-1]) * 100},
        "normalized_locator": {"start": 0},
    }


def state(rows, question="Trích dẫn: quyền nghỉ phép"):
    return {
        "question": question,
        "evidence": {r["evidence_id"]: r for r in rows},
        "bundles": [],
        "plan": understand(question),
        "search_trace": [{"query": question}],
        "iteration": 1,
        "new_count": len(rows),
    }


def test_heading_match_selects_body_and_all_conditions_without_mutating():
    rows = [
        row("e1", "Điều 1. Quyền nghỉ phép", heading=True),
        row("e2", "1. Người làm việc đủ năm có quyền nghỉ.", node="clause"),
        row("e3", "2. Trường hợp đặc biệt cần thông báo.", node="exception"),
    ]
    s = state(rows)
    before = copy.deepcopy(s)
    result = select_context(s)
    assert result["selected"] == ["e1", "e2", "e3"]
    assert s == before


def test_chapeau_alone_abstains_but_full_list_survives():
    intro = row("e1", "Quyền nghỉ phép áp dụng trong các trường hợp:", node="intro")
    assert not select_context(state([intro]))["selected"]
    child = row("e2", "a) Được nghỉ khi đủ điều kiện.", ancestors=["article", "intro"])
    assert select_context(state([intro, child]))["selected"] == ["e1", "e2"]


def test_template_false_positive_and_false_negative():
    template = row("e1", "Ngày nghỉ hằng năm:........", scope="form")
    assert not select_context(state([template], "Ngày nghỉ hằng năm thế nào?"))["selected"]
    assert select_context(state([template], "Mẫu ghi ngày nghỉ hằng năm thế nào?"))["selected"] == ["e1"]


def test_omissions_budget_and_different_versions_never_fill_gaps():
    intro = row("e1", "Quyền nghỉ phép trong các trường hợp:", node="intro")
    child = row("e2", "a) quyền nghỉ phép.", version="v2", ancestors=["article", "intro"])
    s = state([intro, child])
    result = select_context(s)
    assert "e1" not in result["selected"]
    s = state([row("e1", "Quyền nghỉ phép được bảo đảm.")])
    s["bundles"] = [{"groups": [{"members": [{"evidence_id": "e1"}], "omitted_chunk_ids": ["missing-exception"]}]}]
    assert not select_context(s)["selected"]
    assert not select_context(state([row("e1", "Quyền nghỉ phép được bảo đảm.")]), max_chars=3)["selected"]


def test_corruption_fails_and_nonsense_never_refines_to_generic_law():
    s = state([row("e1", "Quyền nghỉ phép được bảo đảm.")], "qzzzxxyy qzzzyyyy")
    decision = judge(s, 4, 2)
    result = context_judge(dict(s, context_selection=select_context(s)), decision, 4, 2)
    assert not result["refinement"] and result["stop"] == "NO_SOURCE_GROUNDED_REFINEMENT"
    s["evidence"]["e1"]["quote"] += " changed"
    with pytest.raises(ToolExecutionError):
        select_context(s)


@pytest.mark.pilot_artifacts
def test_timing_and_concurrency_flags(tmp_path):
    from src.applications.tillegal.graphs.legal_qa import LegalQA

    async def exercise():
        qa = LegalQA({"TILLEGAL_CONTEXT_POLICY": "context_judge"})
        results = await asyncio.gather(
            qa.answer("Trích dẫn: quyền nghỉ phép", "one", 1, "draft"),
            qa.answer("qzzzxxyy qzzzyyyy", "two", 1, "draft"),
            return_exceptions=True,
        )
        assert any(isinstance(r, BlockingIOError) for r in results)
        success = next(r for r in results if isinstance(r, dict))
        assert success["stage_timings"]
        assert all(b["request_id"] == success["request_id"] for b in success["evidence_bundles"])

    asyncio.run(exercise())


def test_form_without_article_is_allowed_only_with_explicit_boundary_and_intent():
    template = row("e1", "Ngày nghỉ hằng năm:........", scope="form")
    template["article_id"] = None
    template["ancestry"] = [{"kind": "form", "node_id": "f1"}]
    assert select_context(state([template], "Mẫu ghi ngày nghỉ hằng năm thế nào?"))["selected"] == ["e1"]
    assert not select_context(state([template], "Ngày nghỉ hằng năm thế nào?"))["selected"]


def test_prior_text_cannot_complete_intro_and_version_mismatch_fails():
    prior = row("e1", "Quyền nghỉ phép.", ancestors=["article", "intro"])
    intro = row("e2", "Quyền nghỉ phép trong các trường hợp:", node="intro")
    assert not select_context(state([prior, intro]))["selected"]
    prior["document"]["document_version_id"] = "different"
    with pytest.raises(ToolExecutionError):
        select_context(state([prior]))


def test_quoted_and_generic_terms_are_not_relevant_body():
    quote = row("e1", "Quyền nghỉ phép được bảo đảm.", scope="quoted")
    assert not select_context(state([quote]))["selected"]
    assert not select_context(state([row("e1", "Bộ luật quy định người lao động.")], "Quyền nghỉ phép là gì?"))[
        "selected"
    ]


def test_refinement_prioritizes_topic_heading_over_generic_chapter():
    rows = [row("e1", "Chương XII", heading=True),
            row("e2", "Điều 1. Bảo hiểm xã hội và bảo hiểm y tế", heading=True),
            row("e3", "Nội dung chủ yếu của hợp đồng lao động", heading=True)]
    s = state(rows, "Trích dẫn: bảo hiểm xã hội")
    result = context_judge(dict(s, context_selection=select_context(s)), judge(s, 2, 2), 2, 2)
    assert result["refinement"] == ["Bảo hiểm xã hội và bảo hiểm y tế"]
    assert result["stop"] == "REFINE"


def test_refinement_subject_must_exist_in_source_and_fit_budget():
    rows = [row("e1", "Điều 1. Bảo hiểm xã hội của người lao động", heading=True)]
    s = state(rows, "Trích dẫn: bảo hiểm xã hội")
    result = context_judge(dict(s, context_selection=select_context(s)), judge(s, 2, 2), 2, 2)
    assert result["refinement"] == ["bảo hiểm xã hội người lao động"]
    s["search_trace"].append({"query": result["refinement"][0]})
    result = context_judge(dict(s, context_selection=select_context(s)), judge(s, 2, 2), 2, 2)
    assert result["refinement"] == [] and result["stop"] == "RETRIEVAL_BUDGET"


@pytest.mark.pilot_artifacts
def test_insurance_lookup_retrieves_body_after_source_grounded_refinement():
    from src.applications.tillegal.graphs.legal_qa import LegalQA
    async def exercise():
        qa = LegalQA({"TILLEGAL_CONTEXT_POLICY":"context_judge"})
        result = await qa.answer("Trích dẫn: bảo hiểm xã hội", "insurance-regression", 3, "draft")
        assert result["judgments"][-1]["selected"]
        assert len(result["retrieval_trace"]) <= 4
        assert any(t["query"] == "bảo hiểm xã hội người lao động" for t in result["retrieval_trace"])
    asyncio.run(exercise())


@pytest.mark.parametrize("policy", ["context", "context_judge"])
def test_cancellation_releases_tool_for_next_run(policy):
    from threading import Lock

    from ai_core.rag_generation import MockProvider

    from src.applications.tillegal.graphs.multi_agent import compile_multi
    from src.applications.tillegal.tools.legal_retrieval import SearchInput
    from src.framework.tools.contracts import ToolSpec
    from src.framework.tools.execution import ToolExecutor
    from src.framework.tools.registry import ToolRegistry

    async def exercise():
        started = asyncio.Event()
        stopped = asyncio.Event()

        async def handler(args):
            if args.request_id == "cancel":
                started.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    stopped.set()
            return {
                "request_id": args.request_id,
                "index_id": "index",
                "bundle_id": "bundle",
                "status": "ASSEMBLED",
                "evidence": [row("e1", "Quyền nghỉ phép được bảo đảm.")],
                "groups": [],
            }

        registry = ToolRegistry()
        registry.register(ToolSpec("legal_retrieval", "fixture", SearchInput, handler))
        graph = compile_multi(ToolExecutor(registry), MockProvider(), Lock(), context_policy=policy)
        task = asyncio.create_task(
            graph.ainvoke(
                {
                    "question": "Trích dẫn: quyền nghỉ phép",
                    "request_id": "cancel",
                    "run_id": "cancel-run",
                    "top_k": 1,
                    "workflow": "draft",
                }
            )
        )
        await asyncio.wait_for(started.wait(), 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.wait_for(stopped.wait(), 2)
        result = await graph.ainvoke(
            {
                "question": "Trích dẫn: quyền nghỉ phép",
                "request_id": "next",
                "run_id": "next-run",
                "top_k": 1,
                "workflow": "draft",
            }
        )
        assert result["bundles"][0]["request_id"] == "next"
        assert result["output"]["status"] == "DRAFT"

    asyncio.run(exercise())
