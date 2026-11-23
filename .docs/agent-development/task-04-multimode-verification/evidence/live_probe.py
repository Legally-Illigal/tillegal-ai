"""Task 4 read-only live probe; explicit local checkpoints, no downloads or writes to Supabase."""

import argparse
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path

from dotenv import dotenv_values

from src.applications.tillegal.agents.search.agent import SearchOptions
from src.applications.tillegal.retrieval.reranking_models import RerankConfig
from src.core.config import load_settings
from src.query_search_bootstrap import create_query_search

CACHE = Path("C:/Users/Admin/.cache/huggingface/hub")
E5 = CACHE / "models--intfloat--multilingual-e5-small/snapshots/614241f622f53c4eeff9890bdc4f31cfecc418b3"
RERANK = CACHE / (
    "models--cross-encoder--mmarco-mMiniLMv2-L12-H384-v1/snapshots/1427fd652930e4ba29e8149678df786c240d8825"
)
OUT = Path(".docs/agent-development/task-04-multimode-verification/evidence")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def summary(response):
    result = {
        "type": type(response).__name__,
        "mode": response.mode,
        "status": response.status,
        "evidence_count": len(response.evidence),
        "index": response.index.model_dump(mode="json") if response.index else None,
        "warnings": [w.model_dump(mode="json") for w in response.warnings],
        "error": response.error.model_dump(mode="json") if response.error else None,
        "consistency": response.consistency,
        "evidence": [],
    }
    ranking_fields = {"rank", "raw_score", "score_kind", "retrieval_method"}
    for item in response.evidence:
        row = item.model_dump(mode="json")
        result["evidence"].append(
            {
                key: row[key]
                for key in [
                    "retrieval_chunk_id",
                    "source_document_id",
                    "document_structure_id",
                    "chunk_key",
                    "content_sha256",
                    "hash_check",
                    "rank",
                    "raw_score",
                    "score_kind",
                    "retrieval_method",
                ]
            }
            | {
                "content_hash_matches": hashlib.sha256(item.content.encode()).hexdigest() == item.content_sha256,
                "provenance_digest": digest({k: v for k, v in row.items() if k not in ranking_fields}),
                "source_metadata_digest": digest(item.source_metadata),
                "missing_temporal": item.effective_from is None or item.effective_to is None,
            }
        )
    if hasattr(response, "fusion"):
        result["fusion"] = response.fusion.model_dump(mode="json")
    if hasattr(response, "reranking"):
        result["reranking"] = response.reranking.model_dump(mode="json")
    return result


async def probe(mode):
    raw = Path("e2e-retrieval.json").read_bytes()
    saved = json.loads(raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"))
    options = SearchOptions(
        mode="hybrid" if mode == "rerank" else mode,
        top_k=saved["top_k"],
        as_of_date=saved["as_of_date"],
        allowed_usage_policies=saved["allowed_usage_policies"],
    )
    report = {
        "probe": mode,
        "question": "Trích dẫn: hợp đồng dân sự",
        "options": options.model_dump(mode="json"),
        "service_timeout_seconds": 30,
        "rerank_total_timeout_seconds": 40 if mode == "rerank" else None,
    }
    try:
        for path in ([E5] if mode in {"dense", "hybrid", "rerank"} else []) + ([RERANK] if mode == "rerank" else []):
            if not all((path / f).is_file() for f in ("config.json", "tokenizer.json", "model.safetensors")):
                report.update(status="BLOCKED", reason="MODEL_FILES_UNAVAILABLE", model_path=str(path))
                return report
        settings = load_settings(environ=dotenv_values(".env")).supabase
        if not settings.is_configured:
            report.update(status="BLOCKED", reason="SUPABASE_NOT_CONFIGURED")
            return report
        pipeline = create_query_search(
            settings,
            options,
            dense_model_path=E5 if mode != "bm25" else None,
            rerank_config=RerankConfig(enabled=True, model_path=RERANK) if mode == "rerank" else None,
        )
        started = time.perf_counter()
        state = await asyncio.wait_for(pipeline.search(report["question"]), timeout=45)
        report["elapsed_seconds"] = time.perf_counter() - started
        report["status"] = state["status"]
        report["plan"] = state["plan"]
        report["requests"] = [req.model_dump(mode="json") for req in state["requests"]]
        report["responses"] = [summary(r) for r in state["responses"]]
        report["legacy_modules_loaded"] = sorted(n for n in sys.modules if n == "ai_core" or n.startswith("ai_core."))
        if mode == "bm25":
            started = time.perf_counter()
            direct = await pipeline.retrieval.search(state["requests"][0])
            report["direct_elapsed_seconds"] = time.perf_counter() - started
            report["direct"] = summary(direct)
            fields = {"request_id", "retrieved_at"}
            report["direct_parity_excluding_ids_time"] = direct.model_dump(exclude=fields) == state["responses"][
                0
            ].model_dump(exclude=fields)
            report["same_observed_index"] = direct.index == state["responses"][0].index
        if mode != "bm25":
            encoder = pipeline.retrieval._query_embedder
            report["e5_local_path"] = str(E5)
            report["encoder_loaded"] = encoder._model is not None
            if encoder._model is not None:
                report["encoder_dimension"] = encoder._model.get_sentence_embedding_dimension()
                report["encoder_max_seq_length"] = encoder._model.max_seq_length
        if mode == "rerank":
            report["reranker_local_path"] = str(RERANK)
    except Exception as error:
        report.update(status="BLOCKED", exception_type=type(error).__name__)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("bm25", "dense", "hybrid", "rerank"))
    mode = parser.parse_args().mode
    report = asyncio.run(probe(mode))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"live-{mode}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k
                in {
                    "probe",
                    "status",
                    "elapsed_seconds",
                    "exception_type",
                    "direct_parity_excluding_ids_time",
                    "same_observed_index",
                    "encoder_dimension",
                }
            },
            ensure_ascii=True,
        )
    )
    for row in report.get("responses", []):
        print(
            json.dumps(
                {
                    "status": row["status"],
                    "count": row["evidence_count"],
                    "error": row["error"],
                    "reranking_status": row.get("reranking", {}).get("status"),
                },
                ensure_ascii=True,
            )
        )
