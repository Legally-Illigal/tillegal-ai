"""Invented sources for plumbing and human review, NOT real law or semantic gold."""

from copy import deepcopy

from src.applications.tillegal.retrieval.bm25 import digest

from .summary_fixture import fixture_input


def partial_case():
    value, model, _ = fixture_input()
    evidence = value["evidence_bundle"]["evidence"]
    rule = next(e for e in evidence if "Đơn vị mẫu" in e["quote"])
    exception = next(e for e in evidence if "Ngoại lệ giả định:" in e["quote"])
    neighbor = next(e for e in evidence if e not in (rule, exception))
    value["question"] = "Nguồn giả định nêu gì và đã đủ để kết luận áp dụng cho tình huống của tôi chưa?"
    value["query_plan"]["issues"] = [
        {"issue_id": "I1", "text": "Quy tắc mẫu và khả năng áp dụng khi chưa đủ dữ kiện"},
        {"issue_id": "I2", "text": "Nội dung đoạn ngoại lệ giả định"},
    ]
    groups = []
    for rank, (seed, members) in enumerate(((rule, [rule, neighbor]), (exception, [exception])), 1):
        group = deepcopy(value["evidence_bundle"]["groups"][0])
        group.update(
            retrieved_chunk_id=seed["chunk_id"],
            rank=rank,
            omitted_chunk_ids=[],
            seed_included=True,
            members=[{"evidence_id": e["evidence_id"], "role": "RETRIEVED"} for e in members],
        )
        groups.append(group)
    value["evidence_bundle"]["groups"] = groups
    value["evidence_bundle"]["bundle_id"] = "bundle:" + digest(
        {k: v for k, v in value["evidence_bundle"].items() if k != "bundle_id"}
    )
    value["judge_result"].update(
        status="INSUFFICIENT",
        issue_checks=[
            {"issue_id": "I1", "coverage": "partial", "evidence_ids": [rule["evidence_id"], neighbor["evidence_id"]]},
            {"issue_id": "I2", "coverage": "full", "evidence_ids": [exception["evidence_id"]]},
        ],
        usable_evidence_ids=[rule["evidence_id"], exception["evidence_id"]],
        missing_items=["I1: Chưa có đủ dữ kiện điều kiện B và ngoại lệ C để kết luận áp dụng."],
        next_queries=[],
    )
    model["units"] = [
        {
            "text": "Đoạn nguồn giả định nêu điều kiện B cho việc tổ chức đối thoại với nhóm A.",
            "issue_ids": ["I1"],
            "evidence_ids": [rule["evidence_id"]],
            "statement_type": "source_statement",
        },
        {
            "text": "Đoạn ngoại lệ giả định nêu không áp dụng quy tắc mẫu khi có điều kiện C.",
            "issue_ids": ["I2"],
            "evidence_ids": [exception["evidence_id"]],
            "statement_type": "source_statement",
        },
    ]
    model["limitations"] = ["I1: Chỉ mô tả nội dung đoạn nguồn, chưa kết luận cho tình huống người dùng."]
    return value, model
