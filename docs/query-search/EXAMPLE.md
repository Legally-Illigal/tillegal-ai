# Ví dụ thực thi Query → Search → Retrieval

Đây là output thực tế được tạo khi chạy code sau thay đổi. Semantic model được **mock**, RetrievalService và logic hydrate/kiểm tra hash là code thật, database ports dùng fixture tổng hợp có nhãn rõ. Nội dung fixture không phải văn bản pháp luật và không chứng minh tính liên quan/chính xác pháp lý. Không có câu trả lời pháp luật được tạo.

Câu hỏi có hợp đồng 2 năm, làm 6 tháng, muốn nghỉ việc và hai mục tiêu báo trước/bồi thường. Model fixture tách hai mục tiêu, facts giữ trích đoạn có trong câu hỏi, ghi nhận thiếu lý do nghỉ. `QuerySearch.search` → `SemanticQueryAgent.understand` → injected StructuredCompletion (mock một lần) → validate → `search` → `RetrievalService.search` hai lần (BM25) → tokenizer/index/sparse/hydration/hash/eligibility → `_finish`.

Hai response đều có hai chunk giống nhau, nên tổng bốn lần xuất hiện được gom thành hai bằng chứng với hai occurrences mỗi bằng chứng. Mỗi occurrence giữ query/rank/score/request ID. Cảnh báo thiếu URL và thời gian từ fixture được giữ. `COMPLETE` chỉ xác nhận hai thao tác tìm hoàn tất.

```json
{
  "question": "Tôi ký hợp đồng lao động 2 năm, mới làm được 6 tháng nhưng muốn nghỉ việc. Tôi có phải báo trước không và có phải bồi thường không?",
  "execution": "Mocked semantic model -> real QuerySearch/Search/RetrievalService -> synthetic read ports",
  "plan": {
    "original": "Tôi ký hợp đồng lao động 2 năm, mới làm được 6 tháng nhưng muốn nghỉ việc. Tôi có phải báo trước không và có phải bồi thường không?",
    "intent": "legal_question",
    "domain": "labour",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "người lao động hợp đồng 2 năm nghỉ việc báo trước",
        "purpose": "question_part"
      },
      {
        "text": "người lao động hợp đồng 2 năm nghỉ việc bồi thường",
        "purpose": "question_part"
      }
    ],
    "clarification": null,
    "analysis_method": "llm",
    "analysis_model": "fixture/structured-model",
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
      "Lý do nghỉ việc là gì?"
    ]
  },
  "requests": [
    {
      "query": "người lao động hợp đồng 2 năm nghỉ việc báo trước",
      "mode": "bm25",
      "top_k": 5,
      "as_of_date": "2026-11-10",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ]
    },
    {
      "query": "người lao động hợp đồng 2 năm nghỉ việc bồi thường",
      "mode": "bm25",
      "top_k": 5,
      "as_of_date": "2026-11-10",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ]
    }
  ],
  "response_summary": [
    {
      "query": "người lao động hợp đồng 2 năm nghỉ việc báo trước",
      "status": "OK",
      "mode": "bm25",
      "evidence_ids": [
        "00000000-0000-0000-0000-000000000002",
        "00000000-0000-0000-0000-000000000001"
      ],
      "warning_codes": [
        "SOURCE_URL_MISSING",
        "TEMPORAL_METADATA_INCOMPLETE",
        "SOURCE_URL_MISSING",
        "TEMPORAL_METADATA_INCOMPLETE"
      ]
    },
    {
      "query": "người lao động hợp đồng 2 năm nghỉ việc bồi thường",
      "status": "OK",
      "mode": "bm25",
      "evidence_ids": [
        "00000000-0000-0000-0000-000000000002",
        "00000000-0000-0000-0000-000000000001"
      ],
      "warning_codes": [
        "SOURCE_URL_MISSING",
        "TEMPORAL_METADATA_INCOMPLETE",
        "SOURCE_URL_MISSING",
        "TEMPORAL_METADATA_INCOMPLETE"
      ]
    }
  ],
  "status": "COMPLETED",
  "completeness": "COMPLETE",
  "executed_searches": 2,
  "evidence": [
    {
      "evidence": {
        "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002",
        "source_document_id": "00000000-0000-0000-0000-00000000001e",
        "document_structure_id": "00000000-0000-0000-0000-000000000028",
        "chunk_key": "chunk-2",
        "content": "FIXTURE TỔNG HỢP, KHÔNG PHẢI VĂN BẢN LUẬT: Mục tra cứu nghĩa vụ bồi thường và thỏa thuận đào tạo khi nghỉ việc.",
        "content_sha256": "aaf037b99e5ecc196f8f3ed30f3b86a5f1c290fa2b6ea05438d18e7323547dd6",
        "hash_check": "MATCHED_STORED",
        "content_representation": "retrieval_chunk_content",
        "rank": 1,
        "raw_score": 7.2,
        "score_kind": "BM25",
        "retrieval_method": "bm25",
        "node_id": null,
        "block_id": null,
        "chunk_type": "text",
        "start_offset": null,
        "end_offset": null,
        "chunk_metadata": {
          "fixture": true,
          "topic": "nghĩa vụ bồi thường và thỏa thuận đào tạo"
        },
        "source_id": null,
        "source_record_id": null,
        "source_snapshot_id": null,
        "title": "Tài liệu kiểm thử nghỉ việc — dữ liệu tổng hợp",
        "source_url": null,
        "language": null,
        "issued_on": null,
        "effective_from": "2026-01-01",
        "effective_to": null,
        "effect_status_reported": null,
        "usage_policy": "EXPERIMENTAL_ONLY",
        "source_metadata": {
          "fixture": true
        }
      },
      "occurrences": [
        {
          "subquery_index": 0,
          "response_index": 0,
          "query": "người lao động hợp đồng 2 năm nghỉ việc báo trước",
          "request_id": "581f6f15-13e7-43c5-a7d1-f7564b4c6e15",
          "rank": 1,
          "raw_score": 7.2,
          "score_kind": "BM25"
        },
        {
          "subquery_index": 1,
          "response_index": 1,
          "query": "người lao động hợp đồng 2 năm nghỉ việc bồi thường",
          "request_id": "cd05615f-8907-432c-96e0-d38c465b1f19",
          "rank": 1,
          "raw_score": 7.2,
          "score_kind": "BM25"
        }
      ]
    },
    {
      "evidence": {
        "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001",
        "source_document_id": "00000000-0000-0000-0000-00000000001e",
        "document_structure_id": "00000000-0000-0000-0000-000000000028",
        "chunk_key": "chunk-1",
        "content": "FIXTURE TỔNG HỢP, KHÔNG PHẢI VĂN BẢN LUẬT: Mục tra cứu nghĩa vụ báo trước và các trường hợp miễn khi nghỉ việc.",
        "content_sha256": "56a3824ac598dce7e438a628ef253744e2e6c4a912c93ec367a9c6655d24ea8b",
        "hash_check": "MATCHED_STORED",
        "content_representation": "retrieval_chunk_content",
        "rank": 2,
        "raw_score": 5.4,
        "score_kind": "BM25",
        "retrieval_method": "bm25",
        "node_id": null,
        "block_id": null,
        "chunk_type": "text",
        "start_offset": null,
        "end_offset": null,
        "chunk_metadata": {
          "fixture": true,
          "topic": "nghĩa vụ báo trước và các trường hợp miễn"
        },
        "source_id": null,
        "source_record_id": null,
        "source_snapshot_id": null,
        "title": "Tài liệu kiểm thử nghỉ việc — dữ liệu tổng hợp",
        "source_url": null,
        "language": null,
        "issued_on": null,
        "effective_from": "2026-01-01",
        "effective_to": null,
        "effect_status_reported": null,
        "usage_policy": "EXPERIMENTAL_ONLY",
        "source_metadata": {
          "fixture": true
        }
      },
      "occurrences": [
        {
          "subquery_index": 0,
          "response_index": 0,
          "query": "người lao động hợp đồng 2 năm nghỉ việc báo trước",
          "request_id": "581f6f15-13e7-43c5-a7d1-f7564b4c6e15",
          "rank": 2,
          "raw_score": 5.4,
          "score_kind": "BM25"
        },
        {
          "subquery_index": 1,
          "response_index": 1,
          "query": "người lao động hợp đồng 2 năm nghỉ việc bồi thường",
          "request_id": "cd05615f-8907-432c-96e0-d38c465b1f19",
          "rank": 2,
          "raw_score": 5.4,
          "score_kind": "BM25"
        }
      ]
    }
  ],
  "warnings": [
    "SOURCE_URL_MISSING",
    "TEMPORAL_METADATA_INCOMPLETE"
  ],
  "errors": [],
  "skipped_subqueries": [],
  "chunk_read_calls": 2,
  "source_read_calls": 2
}
```
