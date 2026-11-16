"""Task8 read-only live verifier. Run --live explicitly; no downloads/writes to Supabase."""
import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
logging.disable(logging.CRITICAL)

from src.applications.tillegal.retrieval.reranking_models import MODEL_REVISION, RerankConfig
from src.integrations.embeddings.cross_encoder_reranker import LocalCrossEncoder


async def verify(live):
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("peak", "working", "pool_peak", "pool",
                                               "nonpage_peak", "nonpage", "pagefile", "pagefile_peak")]

    def working_set_bytes():
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        if not ctypes.windll.psapi.GetProcessMemoryInfo(wintypes.HANDLE(-1), ctypes.byref(counters), counters.cb):
            raise OSError("Cannot read process memory counters")
        return counters.working
    hub = Path.home() / ".cache/huggingface/hub"
    model = hub / "models--cross-encoder--mmarco-mMiniLMv2-L12-H384-v1/snapshots" / MODEL_REVISION
    config = RerankConfig(enabled=True, model_path=model)
    scorer = LocalCrossEncoder(config)
    result = {"revision": MODEL_REVISION, "runs": [], "live_requested": live,
              "versions": {p: importlib.metadata.version(p) for p in ("torch", "transformers", "sentence-transformers")}}
    output = ROOT / ".docs/development/task8-execution-evidence.json"
    def save():
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    try:
        result["weight_sha256"] = hashlib.sha256((model / "model.safetensors").read_bytes()).hexdigest()
        query = "Điều kiện để hợp đồng dân sự có hiệu lực là gì?"
        texts = ("Các bên tự nguyện giao kết hợp đồng và có năng lực hành vi dân sự.", "Quy định đăng ký xe.")
        for kind in ("cold_smoke", "warm_smoke"):
            before = working_set_bytes()
            started = time.perf_counter()
            scores = await scorer.score_pairs(query, texts)
            result["runs"].append({"kind": kind, "text_scope": "ILLUSTRATIVE_NOT_QRELS",
                                   "elapsed_seconds": time.perf_counter() - started,
                                   "rss_before": before, "rss_after": working_set_bytes(),
                                   "diagnostics": scores.model_dump()})
            save()
        import torch
        result["torch_cpu_threads"] = torch.get_num_threads()
        if not live:
            return
        from src.core.config import load_settings
        from src.retrieval_bootstrap import create_retrieval_service
        from src.applications.tillegal.retrieval.contracts import RetrievalRequest
        from postgrest._sync.client import SyncPostgrestClient
        import httpx
        allow = {"get_sparse_index", "get_dense_index", "get_retrieval_chunks", "get_source_document",
                 "search_sparse_legal_chunks", "search_legal_chunks"}
        calls = []
        original_rpc, original_send = SyncPostgrestClient.rpc, httpx.Client.send
        def readonly_rpc(client, function, params, *args, **kwargs):
            if function not in allow:
                raise RuntimeError("Non-allowlisted RPC")
            calls.append(function)
            payload = {k: "{" + ",".join('"' + str(x).replace('\\', '\\\\').replace('"', '\\"') + '"' for x in v) + "}"
                       if isinstance(v, (list, tuple)) else v for k, v in params.items()}
            return original_rpc(client, function, payload, get=True)
        def readonly_send(client, request, *args, **kwargs):
            if request.method != "GET" or "/rpc/" not in request.url.path or request.url.path.rsplit("/", 1)[-1] not in allow:
                raise RuntimeError("Non-read-only HTTP blocked")
            return original_send(client, request, *args, **kwargs)
        SyncPostgrestClient.rpc, httpx.Client.send = readonly_rpc, readonly_send
        try:
            settings = load_settings().supabase
            e5 = hub / "models--intfloat--multilingual-e5-small/snapshots/614241f622f53c4eeff9890bdc4f31cfecc418b3"
            service = create_retrieval_service(settings, dense_model_path=e5, rerank_config=config)
            # Warm E5 separately and report separately, never disguise CE cold-load time.
            started = time.perf_counter()
            await service._query_embedder.encode_query(query)
            result["e5_warmup_seconds"] = time.perf_counter() - started
            request = RetrievalRequest(query=query, mode="hybrid", top_k=5, as_of_date="2026-11-16",
                                       allowed_usage_policies=("EXPERIMENTAL_ONLY",))
            result["request"] = request.model_dump(mode="json")
            for kind in ("live_cold", "live_warm"):
                started = time.perf_counter()
                response = await service.search(request)
                compact = response.model_dump(mode="json")
                compact["evidence"] = [{k: v for k, v in e.items() if k not in ("content", "chunk_metadata", "source_metadata")}
                                       for e in compact["evidence"]]
                result["runs"].append({"kind": kind, "elapsed_seconds": time.perf_counter() - started,
                                       "rss_bytes": working_set_bytes(), "response": compact,
                                       "rpc_calls": list(calls)})
                calls.clear()
                save()
        finally:
            SyncPostgrestClient.rpc, httpx.Client.send = original_rpc, original_send
    except Exception as error:
        result["blocker"] = {"type": type(error).__name__,
                             "safe_code": str(error) if type(error).__name__ == "RerankingOperationalError" else None}
    finally:
        save()
        print(json.dumps({"artifact": output.name, "runs": len(result["runs"]), "blocker": result.get("blocker")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    asyncio.run(verify(parser.parse_args().live))
