"""One read-only BM25 graph smoke; report excludes credentials and raw evidence text."""

import asyncio
import hashlib
import json
import time
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from dotenv import dotenv_values
from langsmith import tracing_context

from src.applications.tillegal.agents.search.agent import SearchOptions
from src.applications.tillegal.graphs.legal_qa import QuerySearchWorkflow
from src.applications.tillegal.state.legal_qa_state import JudgeHandoff
from src.core.config import load_settings
from src.framework.runtime.execution_context import ExecutionContext
from src.framework.runtime.lifecycle import ExecutionLifecycle
from src.query_search_bootstrap import create_query_search


async def smoke():
    raw = Path("e2e-retrieval.json").read_bytes()
    saved = json.loads(raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"))
    options = SearchOptions(
        mode="bm25",
        top_k=saved["top_k"],
        as_of_date=saved["as_of_date"],
        allowed_usage_policies=saved["allowed_usage_policies"],
    )
    report = {"question": "Trích dẫn: hợp đồng dân sự", "options": options.model_dump(mode="json")}
    try:
        pipeline = create_query_search(load_settings(environ=dotenv_values(".env")).supabase, options)
        workflow = QuerySearchWorkflow(pipeline)
        lifecycle = ExecutionLifecycle()
        context = ExecutionContext(run_id=str(uuid4()), request_id="task-05-bm25-smoke")
        with patch.object(pipeline.retrieval, "search", wraps=pipeline.retrieval.search) as calls:
            started = time.perf_counter()
            with tracing_context(enabled=False):
                state = await workflow.execute(report["question"], context, timeout_seconds=35, lifecycle=lifecycle)
            report["elapsed_seconds"] = time.perf_counter() - started
            report["retrieval_calls"] = calls.await_count
        packet = state["handoff"]
        restored = JudgeHandoff.model_validate_json(packet.model_dump_json())
        report.update(
            graph_status=state["status"],
            lifecycle_status=lifecycle.snapshot.status,
            handoff_status=packet.status,
            handoff_roundtrip_equal=restored == packet,
            run_id_preserved=packet.run_id == context.run_id,
            request_id_preserved=packet.request_id == context.request_id,
            response_statuses=[r.status for r in packet.responses],
            evidence_counts=[len(r.evidence) for r in packet.responses],
            warning_codes=[w.code for w in packet.warnings],
            error_codes=[e.code for e in packet.errors],
            content_hashes_match=all(
                hashlib.sha256(e.content.encode()).hexdigest() == e.content_sha256
                for r in packet.responses
                for e in r.evidence
            ),
            response_types=[type(r).__name__ for r in packet.responses],
            evidence_ids=[[str(e.retrieval_chunk_id) for e in r.evidence] for r in packet.responses],
        )
    except Exception as error:
        report.update(graph_status="EXECUTION_FAILED", exception_type=type(error).__name__)
    return report


if __name__ == "__main__":
    report = asyncio.run(smoke())
    Path(".docs/agent-development/task-05-langgraph-integration/evidence/live-bm25.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=True))
