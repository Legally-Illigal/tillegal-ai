"""Reproducible invented source + real parser/BM25/Builder; fixture LLM responses."""

from src.applications.tillegal.agents.response.adapter import make_summary_input
from src.applications.tillegal.ingestion.data_contracts import NULLABLE_FIELDS, build_document
from src.applications.tillegal.ingestion.legal_parser import parse_document
from src.applications.tillegal.retrieval.bm25 import (
    ALGORITHM_VERSION,
    DEFAULT_CONFIG,
    INDEX_SCHEMA,
    TOKENIZER,
    BM25Index,
    term_statistics,
)
from src.applications.tillegal.retrieval.evidence_builder import EvidenceBuilder


def fixture_index(source=None):
    values = {k: None for k in NULLABLE_FIELDS}
    values.update(source_url="https://example.invalid/summary-fixture", title="Nguồn giả định, không phải pháp luật")
    document = build_document(
        **values,
        source_id="synthetic",
        source_record_id="summary-fixture",
        source_snapshot_id="a" * 64,
        content_format="text",
        content="VÍ DỤ GIẢ ĐỊNH, KHÔNG PHẢI PHÁP LUẬT\nĐiều 1. Quy tắc mẫu\n"
        "1. Đơn vị mẫu tổ chức đối thoại với nhóm A khi có điều kiện B.\n"
        "2. Ngoại lệ giả định: không áp dụng quy tắc mẫu khi có điều kiện C.\n",
        raw_ref={
            "uri": "fixture:///summary.txt",
            "file_sha256": "b" * 64,
            "record_key": "id",
            "record_value": "summary-fixture",
        },
        processing_steps=["synthetic_summary_fixture"],
        issues=["SYNTHETIC_NOT_LAW"],
    )
    parsed = parse_document(document)
    chunks = sorted(parsed["chunks"], key=lambda c: c["chunk_id"])
    return BM25Index(
        {
            "schema_version": INDEX_SCHEMA,
            "algorithm_version": ALGORITHM_VERSION,
            "tokenizer": TOKENIZER,
            "config": DEFAULT_CONFIG,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "approved_for_legal_verification": False,
            "corpus_snapshot_id": None,
            "source": source or {"fixture": "SYNTHETIC_NOT_LAW", "processed_snapshot_id": "c" * 64},
            "documents": [{k: v for k, v in document.to_dict().items() if k != "content"}],
            "nodes": {document.document_version_id: parsed["nodes"]},
            "chunks": chunks,
            "statistics": term_statistics(chunks),
        }
    )


def fixture_input(index=None):
    index = index or fixture_index()
    context = {
        "request_id": "summary-fixture",
        "question": "Theo nguồn giả định, quy tắc đối thoại và ngoại lệ là gì?",
        "query_plan": {"issues": [{"issue_id": "I1", "text": "Quy tắc và ngoại lệ giả định"}]},
        "as_of_date": "2026-11-01",
    }
    bundle = EvidenceBuilder(index).build(index.search(context["question"], 3), request_id=context["request_id"])
    ids = [e["evidence_id"] for e in bundle["evidence"]]
    judge = {
        "status": "SUFFICIENT",
        "issue_checks": [{"issue_id": "I1", "coverage": "full", "evidence_ids": ids}],
        "usable_evidence_ids": ids[:],
        "missing_items": [],
        "next_queries": [],
        "explanation": "FIXTURE: nhãn có chủ đích để test plumbing; không phải đánh giá của LLM.",
        "error_code": None,
    }
    clause = next(e["evidence_id"] for e in bundle["evidence"] if "Đơn vị mẫu" in e["quote"])
    model = {
        "units": [
            {
                "text": "Theo ví dụ giả định, đơn vị mẫu tổ chức đối thoại với nhóm A khi có điều kiện B.",
                "issue_ids": ["I1"],
                "evidence_ids": [clause],
                "statement_type": "source_statement",
            }
        ],
        "limitations": ["FIXTURE: chỉ kiểm tra plumbing; chưa đánh giá chất lượng nội dung."],
        "abstain": False,
    }
    return (
        make_summary_input(
            bundle,
            judge,
            question=context["question"],
            query_plan=context["query_plan"],
            as_of_date=context["as_of_date"],
        ),
        model,
        context,
    )
