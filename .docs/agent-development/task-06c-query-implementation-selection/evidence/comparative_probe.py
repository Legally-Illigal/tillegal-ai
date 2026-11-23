"""Offline source comparison, loading the WIP by path without copying or editing it."""

import asyncio
import importlib.util
import json
import sys
import unicodedata
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID

from pydantic import ValidationError

from src.applications.tillegal.agents.query.agent import QueryPlan as APlan
from src.applications.tillegal.agents.query.agent import understand
from src.applications.tillegal.agents.search.agent import search
from tests.unit.applications.tillegal.test_query_search_multimode import options

OUT = Path(".docs/agent-development/task-06c-query-implementation-selection/evidence")
B_ROOT = Path("D:/DOWNLOAD/tillegal-ai/retrieval-publish/src/applications/tillegal/agents/query")
spec = importlib.util.spec_from_file_location(
    "selection_wip_query", B_ROOT / "__init__.py", submodule_search_locations=[str(B_ROOT)]
)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
NOW = datetime(2026, 11, 22, 12, tzinfo=UTC)
agent = module.QueryAgent(clock=lambda: NOW, id_factory=lambda: UUID(int=1))


def request(text, **changes):
    data = {
        "request_id": "selection-probe",
        "original_query": text,
        "temporal": {"request_date": "2026-11-22", "as_of_date": "2026-11-22", "origin": "REQUEST_DATE"},
        "source_scope": {"allowed_usage_policies": ["EXPERIMENTAL_ONLY"]},
        "allocation": {"deadline_at": NOW + timedelta(hours=1)},
    }
    data.update(changes)
    return module.QueryAgentInput.model_validate(data)


def error_info(error):
    if isinstance(error, ValidationError):
        return {
            "type": type(error).__name__,
            "details": [{"loc": list(row["loc"]), "type": row["type"]} for row in error.errors()],
        }
    return {"type": type(error).__name__, "message": str(error)}


cases = [
    ("ordinary", "Người lao động nghỉ phép?"),
    ("lookup", "Trích dẫn: đối thoại"),
    ("multipart", "thuế; nghỉ phép; tiền lương"),
    ("A_ambiguity", "Có được không?"),
    ("B_ambiguity", "Tôi bị cho nghỉ, có đúng không?"),
    ("invalid_date", "Quy định ngày 31/02/2024"),
    ("leap_date", "Quy định ngày 29/02/2024"),
    ("literal_NFC", "Khoản 1 Điều 35 quy định gì?"),
    ("literal_NFD", unicodedata.normalize("NFD", "Khoản 1 Điều 35 quy định gì?")),
    ("whitespace", "  Người  lao động\n  nghỉ phép  "),
    ("control_NUL", "abc\x00def ghi chú"),
    ("control_NEL", "ghi\u0085chú pháp luật"),
    ("blank", "   "),
]
observations = []
for label, text in cases:
    row = {"id": label, "label": "OBSERVED", "input": text}
    try:
        row["A"] = understand(text)
    except Exception as error:
        row["A_error"] = error_info(error)
    try:
        row["B"] = agent.plan(request(text)).model_dump(mode="json")
    except Exception as error:
        row["B_error"] = error_info(error)
    observations.append(row)

controls = []
for label, changes in [
    ("unresolved", {"temporal": {"request_date": "2026-11-22", "as_of_date": None, "origin": "UNRESOLVED"}}),
    ("assisted_unsupported", {"processing_mode": "assisted"}),
    ("deadline_expired", {"allocation": {"deadline_at": NOW - timedelta(seconds=1)}}),
    ("context_reference", {"context": [{"message_id": "m1", "role": "user", "content": "Điều 99"}]}),
]:
    result = agent.plan(request("Tra cứu pháp luật", **changes))
    controls.append({"id": label, "label": "OBSERVED", "result": result.model_dump(mode="json")})

A = understand("Trích dẫn: đối thoại")
B = agent.plan(request("Trích dẫn: đối thoại")).model_dump(mode="json")
compatibility = {}
for label, validator, value in [
    ("B_dump_to_APlan", APlan.model_validate, B),
    ("A_dict_to_BPlan", module.QueryPlan.model_validate, A),
]:
    try:
        validator(value)
        compatibility[label] = {"accepted": True}
    except Exception as error:
        compatibility[label] = {"accepted": False, "error": error_info(error)}
service = AsyncMock()
try:
    asyncio.run(search(B, service, options("bm25")))
    compatibility["B_dump_to_A_Search"] = {"accepted": True}
except Exception as error:
    compatibility["B_dump_to_A_Search"] = {
        "accepted": False,
        "error": error_info(error),
        "retrieval_calls": service.search.await_count,
    }
for label, text in [
    ("A_clarification_Search", "Có được không?"),
    ("A_invalid_date_Search", "Quy định ngày 31/02/2024"),
]:
    svc = AsyncMock()
    result = asyncio.run(search(understand(text), svc, options("bm25")))
    compatibility[label] = {"status": result["status"], "retrieval_calls": svc.search.await_count}

payload = {
    "scope": "Offline synthetic inputs; B loaded from original path under package alias to avoid import collisions",
    "canonical_B_tests": "Executed separately with cwd B, not this alias",
    "A_fields": list(APlan.model_fields),
    "B_fields": list(module.QueryPlan.model_fields),
    "cases": observations,
    "B_control_cases": controls,
    "compatibility": compatibility,
}
(OUT / "comparison-observations.json").write_text(
    json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "cases": len(observations),
            "B_controls": len(controls),
            "A_fields": len(APlan.model_fields),
            "B_fields": len(module.QueryPlan.model_fields),
            "compatibility": compatibility,
        },
        indent=2,
    )
)
