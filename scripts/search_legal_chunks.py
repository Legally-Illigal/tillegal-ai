"""Read-only retrieval CLI. Dense requires an explicit local model directory; never reads .env."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from src.application.services.retrieval_service import RetrievalService
    from src.applications.tillegal.retrieval.hybrid_models import HybridConfig
    from src.applications.tillegal.retrieval.reranking_models import RerankConfig


class _CliArgumentError(ValueError):
    """Argument parser error whose text does not contain user-supplied values."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _CliArgumentError("Invalid CLI arguments; use --help for required options.")


def _configured_service(
    *,
    dense_model_path: Path | None = None,
    hybrid_config: HybridConfig | None = None,
    rerank_config: RerankConfig | None = None,
) -> RetrievalService:
    """Use the existing configuration loader with an explicit environment mapping."""
    from src.core.config import load_settings
    from src.retrieval_bootstrap import create_retrieval_service

    settings = load_settings(environ=os.environ).supabase
    if rerank_config is not None and rerank_config.enabled:
        return create_retrieval_service(
            settings, dense_model_path=dense_model_path, hybrid_config=hybrid_config, rerank_config=rerank_config
        )
    if hybrid_config is not None:
        return create_retrieval_service(settings, dense_model_path=dense_model_path, hybrid_config=hybrid_config)
    if dense_model_path is None:
        return create_retrieval_service(settings)
    return create_retrieval_service(settings, dense_model_path=dense_model_path)


def _exit_code(category: str) -> int:
    return {"INVALID_REQUEST": 2, "INDEX_UNAVAILABLE": 3, "CONFIGURATION_ERROR": 4, "TIMEOUT": 6}.get(category, 5)


def _print_error(category: str, code: str, stage: str, message: str) -> int:
    """Emit a boundary error when a valid retrieval request/response cannot be built."""
    from src.applications.tillegal.retrieval.errors import ErrorCategory, RetrievalErrorDetail

    error = RetrievalErrorDetail(category=ErrorCategory(category), code=code, stage=stage, message=message)
    print(json.dumps({"schema_version": "1", "status": "FAILED", "error": error.model_dump(mode="json")}))
    return _exit_code(category)


def main(argv: list[str] | None = None, *, service_factory: Callable[[], RetrievalService] | None = None) -> int:
    """Validate first, construct dependencies second, then print exactly one JSON outcome."""
    from pydantic import ValidationError

    from src.applications.tillegal.retrieval.contracts import RetrievalMode, RetrievalRequest
    from src.applications.tillegal.retrieval.hybrid_models import HybridConfig
    from src.applications.tillegal.retrieval.reranking_models import RerankConfig

    parser = _Parser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--mode", choices=("bm25", "dense", "hybrid"), default="bm25")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--as-of-date", required=True, help="Explicit YYYY-MM-DD; not the crawl date")
    parser.add_argument("--allowed-policy", action="append", required=True, help="Repeat for each allowed policy")
    parser.add_argument("--dense-model-path", type=Path, help="Existing local E5 checkpoint directory (no download)")
    parser.add_argument("--rrf-k", type=int, default=60, help="Hybrid rank smoothing constant; not a score weight")
    parser.add_argument("--bm25-candidates", type=int, default=20, help="Hybrid BM25 candidate budget (1-50)")
    parser.add_argument("--dense-candidates", type=int, default=20, help="Hybrid Dense candidate budget (1-50)")
    parser.add_argument(
        "--rerank", action="store_true", help="Hybrid only; consume evidence order, not RRF score order"
    )
    parser.add_argument("--rerank-model-path", type=Path)
    parser.add_argument("--rerank-candidates", type=int, default=20)
    parser.add_argument("--rerank-batch-size", type=int, default=4)
    parser.add_argument("--rerank-max-length", type=int, default=512)
    parser.add_argument("--rerank-timeout", type=float, default=10)
    parser.add_argument("--rerank-total-timeout", type=float, default=40)
    try:
        args = parser.parse_args(argv)
        request = RetrievalRequest(
            query=args.query,
            mode=args.mode,
            top_k=args.top_k,
            as_of_date=args.as_of_date,
            allowed_usage_policies=args.allowed_policy,
        )
        hybrid_config = HybridConfig(
            rrf_k=args.rrf_k, bm25_candidates=args.bm25_candidates, dense_candidates=args.dense_candidates
        )
        rerank_config = RerankConfig(
            enabled=args.rerank,
            model_path=args.rerank_model_path,
            candidate_pool=args.rerank_candidates,
            batch_size=args.rerank_batch_size,
            max_length=args.rerank_max_length,
            inference_timeout_seconds=args.rerank_timeout,
            total_timeout_seconds=args.rerank_total_timeout,
        )
        if args.rerank and (args.mode != "hybrid" or args.rerank_model_path is None):
            raise _CliArgumentError("Reranking requires hybrid and explicit model path")
    except (_CliArgumentError, ValidationError):
        return _print_error(
            "INVALID_REQUEST",
            "INVALID_ARGUMENTS",
            "validation",
            "Invalid search arguments; check query, date, policies and top-k (1-50).",
        )
    except SystemExit as exit_status:
        return int(exit_status.code or 0)
    if request.mode in (RetrievalMode.DENSE, RetrievalMode.HYBRID) and args.dense_model_path is None:
        return _print_error(
            "CONFIGURATION_ERROR", "MODE_NOT_CONFIGURED", "validation", "Dense/Hybrid requires --dense-model-path."
        )
    try:
        if service_factory:
            service = service_factory()
        elif request.mode == RetrievalMode.HYBRID:
            service = _configured_service(
                dense_model_path=args.dense_model_path,
                hybrid_config=hybrid_config,
                **({"rerank_config": rerank_config} if rerank_config.enabled else {}),
            )
        else:
            service = _configured_service(
                dense_model_path=args.dense_model_path if request.mode == RetrievalMode.DENSE else None,
            )
    except Exception:
        # Third-party configuration/client exceptions can contain keys or URLs.
        # Do not render them, and do not treat configuration failure as no-match.
        return _print_error(
            "CONFIGURATION_ERROR",
            "RETRIEVAL_CONFIGURATION_FAILED",
            "configuration",
            "Cannot construct retrieval dependencies; check the process configuration.",
        )
    try:
        response = asyncio.run(service.search(request))
    except ValidationError:
        return _print_error(
            "INCONSISTENT_EVIDENCE", "INVALID_SERVICE_RESPONSE", "response", "Retrieval output violates its contract."
        )
    except Exception:
        return _print_error(
            "INCONSISTENT_EVIDENCE",
            "UNEXPECTED_RETRIEVAL_FAILURE",
            "search",
            "Unexpected retrieval failure; no partial evidence was returned.",
        )
    print(response.model_dump_json())
    return 0 if response.error is None else _exit_code(response.error.category)


if __name__ == "__main__":
    if __package__ in (None, ""):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
