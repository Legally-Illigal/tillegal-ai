"""Offline acceptance demo of the existing QuerySearch entry point; no network or LLM calls."""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from pydantic import TypeAdapter

from src.applications.tillegal.agents.query.agent import QueryInputError, QueryPlan
from src.applications.tillegal.agents.query.schemas import LegalReference, SearchObjective, TemporalContext
from src.applications.tillegal.agents.query.semantic import QueryAnalysisError, SemanticQueryAgent
from src.applications.tillegal.agents.search.agent import SearchOptions, SearchState
from src.applications.tillegal.agents.search.schemas import AggregatedEvidence, EvidenceOccurrence
from src.applications.tillegal.retrieval.contracts import RetrievalRequest, RetrievalResponse, UnifiedEvidence
from src.applications.tillegal.retrieval.errors import RetrievalErrorDetail, RetrievalServiceError
from src.core.config import SupabaseSettings
from src.query_search_bootstrap import QuerySearch, create_query_search

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class FixtureBackend:
    """Serve stored evidence as fixture data; never perform retrieval or confirm relevance."""

    def __init__(self, seed, *, no_match=False, fail_at=None):
        self.seed = seed
        self.calls = 0
        self.no_match = no_match
        self.fail_at = fail_at

    async def search(self, request):
        self.calls += 1
        if self.calls == self.fail_at:
            raise RetrievalServiceError(
                RetrievalErrorDetail(
                    category="DATABASE_FAILURE",
                    code="FIXTURE_READ_FAILED",
                    stage="fixture",
                    message="Controlled acceptance fixture failure.",
                )
            )
        return RetrievalResponse.model_validate(
            {
                **self.seed,
                **request.model_dump(mode="json"),
                "query_used": request.query.strip(),
                "status": "NO_MATCH" if self.no_match else "OK",
                "evidence": [] if self.no_match else self.seed["evidence"],
                "warnings": [] if self.no_match else self.seed["warnings"],
                "error": None,
            }
        )


async def verify():
    prior = ROOT / "evaluation/query_search/semantic_v2"
    saved = load(prior / "gemini.json")
    row = next(row for row in saved["rows"] if row["id"] == "Q004")
    runs = load(prior / "relevance/runs.json")
    seed = next(run for run in runs if run["id"] == "Q004" and run["variant"] == "gemini")["responses"][0]
    options = SearchOptions(
        mode="bm25", top_k=3, as_of_date="2026-11-23", allowed_usage_policies=("EXPERIMENTAL_ONLY",)
    )
    states = {}
    backend = FixtureBackend(seed)
    # Verify the PUBLIC factory delegates to the injected fixture composition.
    with patch("src.query_search_bootstrap.create_retrieval_service", return_value=backend) as composition:
        runner = create_query_search(SupabaseSettings(), options)
        states["deterministic_fixture"] = await runner.search(row["question"])
        composition.assert_called_once()
    assert states["deterministic_fixture"]["plan"]["analysis_method"] == "deterministic"
    assert states["deterministic_fixture"]["completeness"] == "COMPLETE"
    provider_replays = 0

    async def saved_completion(**kwargs):
        nonlocal provider_replays
        provider_replays += 1
        assert json.loads(kwargs["user"])["question"] == row["question"]
        return row["raw_response"]

    planner = SemanticQueryAgent(complete=saved_completion, model=saved["model"], timeout_seconds=30)
    with patch("src.query_search_bootstrap.create_retrieval_service", return_value=FixtureBackend(seed)):
        runner = create_query_search(SupabaseSettings(), options, query_agent=planner)
        states["saved_gemini_raw_replay_fixture"] = await runner.search(row["question"])
    assert provider_replays == 1
    assert states["saved_gemini_raw_replay_fixture"]["plan"]["analysis_method"] == "llm"
    assert (
        states["saved_gemini_raw_replay_fixture"]["plan"]
        == next(r for r in load(prior / "matched.json")["rows"] if r["id"] == "Q004")["plan"]
    )
    states["no_match_fixture"] = await QuerySearch(FixtureBackend(seed, no_match=True), options).search(
        "Điều kiện để hợp đồng dân sự có hiệu lực là gì?"
    )
    assert states["no_match_fixture"]["completeness"] == "COMPLETE"
    assert not states["no_match_fixture"]["evidence"]
    states["partial_failure_fixture"] = await QuerySearch(FixtureBackend(seed, fail_at=2), options).search(
        "Hợp đồng dân sự có hiệu lực thế nào? Người vay trả nợ thế nào? Bảo lãnh thực hiện thế nào?"
    )
    partial = states["partial_failure_fixture"]
    assert partial["completeness"] == "PARTIAL" and partial["skipped_subqueries"] == (2,)
    assert partial["evidence"] and partial["errors"][0].code == "FIXTURE_READ_FAILED"
    states["citation_uncertainty_fixture"] = await QuerySearch(FixtureBackend(seed), options).search(
        "Tra cứu Điều 35 Bộ luật Lao động 45/2019/QH14."
    )
    assert "EXACT_LOOKUP_SOURCE_IDENTITY_UNCONFIRMED" in states["citation_uncertainty_fixture"]["warnings"]
    assert "TEMPORAL_METADATA_INCOMPLETE" in states["deterministic_fixture"]["warnings"]
    errors = []
    try:
        await QuerySearch(FixtureBackend(seed), options).search("")
    except QueryInputError as error:
        errors.append({"scenario": "invalid_input", "code": str(error)})
    for scenario in ("invalid_json", "provider_timeout", "provider_error"):

        async def failure_completion(*, scenario=scenario, **kwargs):
            if scenario == "provider_timeout":
                raise TimeoutError()
            if scenario == "provider_error":
                raise RuntimeError("Controlled fixture error")
            return "{}"

        backend = FixtureBackend(seed)
        try:
            agent = SemanticQueryAgent(complete=failure_completion, model="fixture/acceptance")
            await QuerySearch(backend, options, agent).search(row["question"])
        except QueryAnalysisError as error:
            errors.append({"scenario": scenario, "code": str(error), "search_calls": backend.calls})
    assert len(errors) == 4 and all(e.get("search_calls", 0) == 0 for e in errors)
    adapter = TypeAdapter(SearchState)
    examples = {name: adapter.dump_python(state, mode="json") for name, state in states.items()}
    for state in examples.values():
        adapter.validate_python(state)
    contracts = {
        model.__name__: model.model_json_schema()
        for model in (
            QueryPlan,
            SearchOptions,
            LegalReference,
            TemporalContext,
            SearchObjective,
            EvidenceOccurrence,
            AggregatedEvidence,
            RetrievalRequest,
            RetrievalResponse,
            UnifiedEvidence,
            RetrievalErrorDetail,
        )
    }
    contracts["SearchState"] = adapter.json_schema()
    return {
        "kind": "CURRENT_CODE_OFFLINE_CONTROLLED_EXECUTION",
        "new_gemini_calls": 0,
        "new_supabase_calls": 0,
        "raw_provider_origin": "semantic_v2/gemini.json Q004 historical live raw",
        "raw_response_sha256": hashlib.sha256(row["raw_response"].encode()).hexdigest(),
        "backend_origin": "Stored real Supabase evidence reused as fixture; no relevance implied",
        "examples": examples,
        "errors": errors,
        "contracts": contracts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve existing acceptance evidence; choose a new output file")
    report = asyncio.run(verify())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PASS",
                "controlled_states": len(report["examples"]),
                "error_scenarios": len(report["errors"]),
                "new_network_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
