# Input/output và call trace thực tế

> Ghi chú publication: tài liệu ghi lại implementation/acceptance Phase A. Candidate PR được kiểm thử lại độc lập trên main sau V2; trạng thái Git/CI mới nhất được ghi trong FINAL_MAIN_INTEGRATION_REPORT.md (local). Source links đã đổi sang đường dẫn tương đối để review trên GitHub.

**Đây là compiled graph chạy thật với Gemini completion mock và fake Retrieval read ports; không phải live Gemini/Supabase.** Câu hỏi chỉ dùng làm fixture kiểm tra routing/schema, không phải kết luận tư vấn pháp luật. Trace đầy đủ giữ ngoài repo tại `D:\DOWNLOAD\tmp\tillegal-graph-phase-a-20261127\actual_trace.json`; credentials/headers không được đưa vào trace.

## Input mẫu đã thực thi

```json
{
  "question": "Tôi ký hợp đồng lao động 2 năm, mới làm được 6 tháng nhưng muốn nghỉ việc. Tôi có phải báo trước không và có phải bồi thường không?",
  "run_id": "trace-run",
  "request_id": "trace-request"
}
```

Options trusted trong lần chạy:

```json
{
  "mode": "bm25",
  "top_k": 2,
  "as_of_date": "2026-11-10",
  "allowed_usage_policies": [
    "EXPERIMENTAL_ONLY"
  ]
}
```

Graph nhận question/run_id/request_id qua LegalQAState, options đến từ runner. SemanticQueryAgent nhận riêng question string, không nhận một schema mới hoặc payload có credentials từ graph.

## Async call sequence quan sát được

```text
compiled graph.astream(initial_state)
→ query_semantic
→ await existing SemanticQueryAgent.understand(question)
→ existing GeminiStructuredCompletion → mocked _acompletion (1 call)
→ validate structured semantic output / grounding → QueryPlan
→ route_query: không clarification
→ search node → existing search(plan, retrieval, trusted options)
→ 2 RetrievalRequest theo 2 subqueries
→ SearchState + JudgeHandoff V1
→ END
```

Node updates thực tế: `['query', 'search']`. Completion count `1`; native Search executions `2`. Model identifier mock lấy từ cấu hình hiện có `gemini/gemini-3.5-flash-lite`, không hardcode thêm trong graph; timeout/token/schema/retry/log parameters giữ nguyên adapter. Nguồn: [QuerySearchNodes.query_semantic](../../../src/applications/tillegal/graphs/legal_qa.py#L35); [QuerySearchNodes.search](../../../src/applications/tillegal/graphs/legal_qa.py#L54).

## QueryPlan trả ra trong lần chạy

```json
{
  "original": "Tôi ký hợp đồng lao động 2 năm, mới làm được 6 tháng nhưng muốn nghỉ việc. Tôi có phải báo trước không và có phải bồi thường không?",
  "intent": "legal_question",
  "domain": "labour",
  "temporal_scope": [],
  "subqueries": [
    {
      "text": "người lao động hợp đồng 2 năm nghỉ việc báo trước; tình huống người dùng: hợp đồng lao động 2 năm",
      "purpose": "question_part"
    },
    {
      "text": "người lao động hợp đồng 2 năm nghỉ việc bồi thường; tình huống người dùng: hợp đồng lao động 2 năm",
      "purpose": "question_part"
    }
  ],
  "clarification": null,
  "analysis_method": "llm",
  "analysis_model": "gemini-3.5-flash-lite",
  "facts": [
    {
      "text": "hợp đồng lao động 2 năm",
      "source_quote": "hợp đồng lao động 2 năm"
    }
  ],
  "issues": [
    "Nghĩa vụ báo trước",
    "Bồi thường"
  ],
  "missing_information": [
    "Lý do nghỉ việc là gì?",
    "Có thỏa thuận đào tạo hoặc hoàn trả chi phí đào tạo không?"
  ],
  "citations": [],
  "temporal_context": [
    {
      "text": "2 năm",
      "start": 25,
      "end": 30,
      "role": "duration",
      "iso_date": null,
      "negated": false
    },
    {
      "text": "6 tháng",
      "start": 45,
      "end": 52,
      "role": "duration",
      "iso_date": null,
      "negated": false
    }
  ],
  "search_objectives": [
    {
      "query_index": 0,
      "issue_indices": [
        0
      ]
    },
    {
      "query_index": 1,
      "issue_indices": [
        1
      ]
    }
  ],
  "planning_warnings": []
}
```

Search nhận đúng plan này. Test parity dùng factory Gemini hiện có so kwargs model/messages/schema/max_tokens/timeout/num_retries/caching/no-log với facade; graph không đọc key, tạo prompt hoặc sửa schema.

## Search và handoff trả ra

```json
{
  "search": {
    "status": "COMPLETED",
    "completeness": "COMPLETE",
    "warnings": [
      "FIXTURE_WARNING",
      "NO_MATCH:0",
      "NO_MATCH:1"
    ],
    "errors": [],
    "executed_searches": 2,
    "skipped_subqueries": [],
    "evidence_groups": 0
  },
  "handoff": {
    "status": "NO_MATCH",
    "search_status": "COMPLETED",
    "run_id": "trace-run",
    "request_id": "trace-request",
    "response_types": [
      "RetrievalResponse",
      "RetrievalResponse"
    ]
  }
}
```

Fake port trong trace này trả NO_MATCH có FIXTURE_WARNING; không tạo evidence giả để làm đẹp kết quả. Bốn test mode khác dùng native service với fake ports, có evidence thật của fixture, giữ BM25/Dense/Hybrid/Rerank subclasses và JSON roundtrip. Native raw_score của rerank vẫn giữ nghĩa RRF; thứ tự/rank dùng native response, không sort lại theo raw_score.

Hybrid/Rerank native service dispatch thêm hai branch BM25/Dense qua service.search nội bộ: một top-level hybrid request có ba service invocations tính cả hai branch. Đây là composition sẵn có, không duplicate graph Search. Test đếm cả top-level và branch calls; hai semantic issues cùng query text được gộp thành một subquery, giữ cả hai issue_indices.

## Clarification và failure

Clarification từ deterministic guard hoặc model trả về → route_query → END, search_result/handoff=None, không retrieval. Timeout/provider lỗi, non-JSON, JSON sai schema hoặc grounding fail → QueryAnalysisError hiện có, Search không chạy. LangGraph có thể thêm exception note tên node/task ID; error.args/str vẫn là safe code ban đầu, không có raw key/question. Không biến lỗi thành plan deterministic, NO_MATCH hoặc evidence.

Caller task cancellation/token cancellation/deadline đều đã test khi provider đang await. Provider coroutine được cancel, lifecycle báo CANCELLED hoặc FAILED đúng loại; không chạy Search và không có request state dùng chung.
