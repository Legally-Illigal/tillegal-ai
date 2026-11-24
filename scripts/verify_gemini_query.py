"""Explicit Gemini/deterministic verification. No .env loading or secret output."""

import argparse
import asyncio
import json
import time
from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict

from src.application.services.retrieval_service import RetrievalService
from src.applications.tillegal.agents.query.agent import QueryPlan, understand
from src.applications.tillegal.agents.query.gemini import create_gemini_query_agent
from src.applications.tillegal.agents.query.semantic import QueryAnalysisError
from src.applications.tillegal.agents.search.agent import SearchOptions
from src.framework.llm.providers.gemini_adapter import GeminiProviderError
from src.query_search_bootstrap import QuerySearch

EXAMPLE = (
    "Tôi ký hợp đồng lao động 2 năm, mới làm được 6 tháng nhưng muốn nghỉ việc. "
    "Tôi có phải báo trước không và có phải bồi thường không?"
)


class SmokeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    ok: bool


def fixture_retrieval() -> RetrievalService:
    """Real RetrievalService with an empty in-memory sparse index; no database I/O."""
    from src.application.services.retrieval_service import DEFAULT_SPARSE_INDEX
    from src.application.services.vbpl_markdown_indexing_service import tokenize_sparse_text

    class EmptySparse:
        async def search(self, request):
            return ()

    class Index:
        async def get_index(self, name):
            return {
                "id": "00000000-0000-0000-0000-000000000001",
                "index_name": DEFAULT_SPARSE_INDEX,
                "index_version": "v1",
                "status": "READY",
                "updated_at": "2026-11-23T00:00:00Z",
                "algorithm": "BM25",
                "tokenizer": "unicode-nfc-lower-v1",
                "language_config": "simple",
                "k1": 1.2,
                "b": 0.75,
                "document_count": 1,
                "total_token_count": 1,
                "average_document_length": 1,
                "metadata": {"fixture": True},
            }

    class NoHydration:
        def __getattr__(self, name):
            raise AssertionError("Empty fixture must not hydrate evidence")

    return RetrievalService(EmptySparse(), NoHydration(), NoHydration(), Index(), tokenize_sparse_text)


def safe_error(error: Exception) -> dict:
    """Only serialize allowlisted error codes/status, never arbitrary exception text."""
    result = {"code": "QUERY_VERIFICATION_FAILED", "type": type(error).__name__}
    if isinstance(error, QueryAnalysisError):
        result["code"] = str(error)  # SemanticQueryAgent emits fixed content-free codes.
    if isinstance(error, ValueError) and str(error) == "GEMINI_QUERY_CONFIGURATION_INVALID":
        result["code"] = str(error)
    provider_error = error if isinstance(error, GeminiProviderError) else error.__context__
    if isinstance(provider_error, GeminiProviderError):
        result["provider_code"] = provider_error.code
        result["http_status"] = provider_error.http_status
    if isinstance(error, TimeoutError):
        result["code"] = "GEMINI_TIMEOUT"
    return result


async def execute(args: argparse.Namespace) -> dict:
    started = time.perf_counter()
    report = {
        "tested_at": datetime.now(UTC).isoformat(),
        "mode": args.mode,
        "live_gemini": args.mode == "gemini",
        "search_backend": args.search_backend,
    }
    try:
        agent = create_gemini_query_agent() if args.mode == "gemini" else None
        report["model"] = agent.model if agent else None
        if args.smoke_test:
            if agent is None or args.search_backend != "none":
                raise ValueError("Smoke requires Gemini and no search")
            raw = await agent.complete(
                model=agent.model,
                system="Return only a JSON object matching the schema.",
                user='Return {"ok": true}.',
                schema=SmokeResponse.model_json_schema(),
            )
            report["smoke"] = SmokeResponse.model_validate_json(raw).model_dump()
            if not report["smoke"]["ok"]:
                raise ValueError("Unexpected smoke response")
        elif args.search_backend == "none":
            plan = await agent.understand(args.question) if agent else understand(args.question)
            report["plan"] = QueryPlan.model_validate(plan).model_dump()
        else:
            options = SearchOptions(
                mode="bm25",
                top_k=5,
                as_of_date=date.fromisoformat(args.as_of_date),
                allowed_usage_policies=("EXPERIMENTAL_ONLY",),
            )
            result = await QuerySearch(fixture_retrieval(), options, agent).search(args.question)
            report["plan"] = QueryPlan.model_validate(result["plan"]).model_dump()
            report["search"] = {
                "status": result["status"],
                "completeness": result["completeness"],
                "executed_searches": result["executed_searches"],
                "queries": [request.query for request in result["requests"]],
                "response_statuses": [response.status for response in result["responses"]],
                "evidence_count": len(result["evidence"]),
                "warnings": result["warnings"],
            }
            if result["status"] == "FAILED":
                raise ValueError("Fixture retrieval failed")
        report["status"] = "PASS"
    except Exception as error:
        report["status"] = "FAIL"
        report["error"] = safe_error(error)
    report["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("deterministic", "gemini"), default="deterministic")
    parser.add_argument("--question", default=EXAMPLE)
    parser.add_argument("--smoke-test", action="store_true", help="One minimal LIVE Gemini JSON request")
    parser.add_argument("--search-backend", choices=("none", "fixture"), default="none")
    parser.add_argument("--as-of-date", default="2026-11-23", help="Explicit fixture retrieval date")
    args = parser.parse_args(argv)
    result = asyncio.run(execute(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
