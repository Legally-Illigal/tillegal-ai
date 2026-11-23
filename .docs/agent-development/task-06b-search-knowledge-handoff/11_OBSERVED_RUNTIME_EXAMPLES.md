# Observed Search runtime examples

**18 traces chi tiết** và bảng 35 Search cases, 9 graph invocations. Tất cả executions mới là offline; data synthetic/fixtures, không Supabase hoặc model inference thật. [JSON đầy đủ](evidence/search-traces.json) chứa source_line_snapshots từ sys.settrace trên chính Search coroutine code object. Không gọi đây là formal branch coverage.

Các JSON dưới đây là OBSERVED projections: input/options/events/final state hoặc exception lấy từ artifact. Native response được serialize chỉ để trình bày; runtime SearchState giữ typed objects. Handoff trong direct cases do diagnostic harness gọi riêng sau Search để kiểm boundary; graph cases mới là packet do Search node tạo.

## 1. one_bm25 — OBSERVED

Plan từ understand của quote request; native BM25 response OK và 2 evidence. Handoff được harness gọi tường minh, không phải Search tự tạo.

Backend: real RetrievalService with fake read/model ports.

```json
{
  "input_plan": {
    "original": "Trích dẫn: thuế",
    "intent": "quote_lookup",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "thuế",
        "purpose": "lookup"
      }
    ],
    "clarification": null
  },
  "options": {
    "mode": "bm25",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "call_events": [
    {
      "event": "start",
      "number": 1,
      "query": "thuế"
    },
    {
      "event": "return",
      "number": 1,
      "status": "OK"
    }
  ],
  "search_state": {
    "plan": {
      "original": "Trích dẫn: thuế",
      "intent": "quote_lookup",
      "domain": "unknown",
      "temporal_scope": [],
      "subqueries": [
        {
          "text": "thuế",
          "purpose": "lookup"
        }
      ],
      "clarification": null
    },
    "requests": [
      {
        "query": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ]
      }
    ],
    "responses": [
      {
        "schema_version": "1",
        "request_id": "4d75c2f7-d7e4-486e-aeb7-f1ccba54caca",
        "query": "thuế",
        "query_used": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ],
        "selected_index_name": "vbpl-bm25-unicode-v1",
        "index": {
          "id": "00000000-0000-0000-0000-000000000014",
          "index_name": "vbpl-bm25-unicode-v1",
          "index_version": "v1",
          "status": "READY",
          "updated_at": "2026-11-10T00:00:00Z",
          "algorithm": "BM25",
          "tokenizer": "unicode-nfc-lower-v1"
        },
        "status": "OK",
        "evidence": [
          {
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001",
            "source_document_id": "00000000-0000-0000-0000-00000000001e",
            "document_structure_id": "00000000-0000-0000-0000-000000000028",
            "chunk_key": "chunk-1",
            "content": "Demo > Điều 1 > Thuế 1.",
            "content_sha256": "357303a997e14de6aa3e9b8603ac96241b9816c75e9a4bb0d49ab30703d06ab2",
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
              "breadcrumb": "Demo > Điều 1"
            },
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": null,
            "title": "Demo",
            "source_url": null,
            "language": "vi",
            "issued_on": null,
            "effective_from": null,
            "effective_to": null,
            "effect_status_reported": null,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {}
          },
          {
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002",
            "source_document_id": "00000000-0000-0000-0000-00000000001e",
            "document_structure_id": "00000000-0000-0000-0000-000000000028",
            "chunk_key": "chunk-2",
            "content": "Demo > Điều 1 > Thuế 2.",
            "content_sha256": "dd9314bb58dd5dfa69a24b00571195f1ee0d4bd47d384e0486ed978396fef1c0",
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
              "breadcrumb": "Demo > Điều 1"
            },
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": null,
            "title": "Demo",
            "source_url": null,
            "language": "vi",
            "issued_on": null,
            "effective_from": null,
            "effective_to": null,
            "effect_status_reported": null,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {}
          }
        ],
        "warnings": [
          {
            "code": "SOURCE_URL_MISSING",
            "message": "Source URL is unavailable.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001"
          },
          {
            "code": "TEMPORAL_METADATA_INCOMPLETE",
            "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001"
          },
          {
            "code": "SOURCE_URL_MISSING",
            "message": "Source URL is unavailable.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002"
          },
          {
            "code": "TEMPORAL_METADATA_INCOMPLETE",
            "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002"
          }
        ],
        "error": null,
        "retrieved_at": "2026-11-21T15:06:50.728335Z",
        "consistency": "BEST_EFFORT"
      }
    ],
    "status": "COMPLETED"
  }
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "response_types": [
    "RetrievalResponse"
  ],
  "plan_identity_preserved": true,
  "plan_unchanged": true,
  "response_identity_preserved": true,
  "max_active_calls": 1,
  "evidence_payload_hashes_match": true,
  "handoff_warning_codes": [
    "SOURCE_URL_MISSING",
    "TEMPORAL_METADATA_INCOMPLETE",
    "SOURCE_URL_MISSING",
    "TEMPORAL_METADATA_INCOMPLETE"
  ],
  "handoff_error_codes": [],
  "handoff_roundtrip_equal": true,
  "handoff_roundtrip_types": [
    "RetrievalResponse"
  ],
  "handoff_projection": {
    "schema_version": "1",
    "question": "Trích dẫn: thuế",
    "request_id": "fixture-request",
    "run_id": "fixture-run",
    "options": {
      "mode": "bm25",
      "top_k": 2,
      "as_of_date": "2026-11-10",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ]
    },
    "search_status": "COMPLETED",
    "status": "READY"
  },
  "handoff_full_payload": "See search-traces.json/search_traces/one_bm25/handoff"
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[
  {
    "line_about_to_execute": 42,
    "request_count": null,
    "responses_accumulated": null
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 0
  },
  {
    "line_about_to_execute": 49,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 56,
    "request_count": 1,
    "responses_accumulated": 1
  }
]
```

## 2. multi_success — OBSERVED

3 explicit subqueries, 3 calls tuần tự, top_k 2 mỗi call, tổng 6 evidence occurrences. Không có global ranking hoặc cross-response dedup.

Backend: real RetrievalService with fake read/model ports.

```json
{
  "input_plan": {
    "original": "thuế; hợp đồng; bảo hiểm",
    "intent": "legal_question",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "thuế",
        "purpose": "question_part"
      },
      {
        "text": "hợp đồng",
        "purpose": "question_part"
      },
      {
        "text": "bảo hiểm",
        "purpose": "question_part"
      }
    ],
    "clarification": null
  },
  "options": {
    "mode": "bm25",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "call_events": [
    {
      "event": "start",
      "number": 1,
      "query": "thuế"
    },
    {
      "event": "return",
      "number": 1,
      "status": "OK"
    },
    {
      "event": "start",
      "number": 2,
      "query": "hợp đồng"
    },
    {
      "event": "return",
      "number": 2,
      "status": "OK"
    },
    {
      "event": "start",
      "number": 3,
      "query": "bảo hiểm"
    },
    {
      "event": "return",
      "number": 3,
      "status": "OK"
    }
  ],
  "search_state": {
    "plan": {
      "original": "thuế; hợp đồng; bảo hiểm",
      "intent": "legal_question",
      "domain": "unknown",
      "temporal_scope": [],
      "subqueries": [
        {
          "text": "thuế",
          "purpose": "question_part"
        },
        {
          "text": "hợp đồng",
          "purpose": "question_part"
        },
        {
          "text": "bảo hiểm",
          "purpose": "question_part"
        }
      ],
      "clarification": null
    },
    "requests": [
      {
        "query": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ]
      },
      {
        "query": "hợp đồng",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ]
      },
      {
        "query": "bảo hiểm",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ]
      }
    ],
    "responses": [
      {
        "schema_version": "1",
        "request_id": "66ea47ff-e89f-425e-8213-9864f60cc149",
        "query": "thuế",
        "query_used": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ],
        "selected_index_name": "vbpl-bm25-unicode-v1",
        "index": {
          "id": "00000000-0000-0000-0000-000000000014",
          "index_name": "vbpl-bm25-unicode-v1",
          "index_version": "v1",
          "status": "READY",
          "updated_at": "2026-11-10T00:00:00Z",
          "algorithm": "BM25",
          "tokenizer": "unicode-nfc-lower-v1"
        },
        "status": "OK",
        "evidence": [
          {
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001",
            "source_document_id": "00000000-0000-0000-0000-00000000001e",
            "document_structure_id": "00000000-0000-0000-0000-000000000028",
            "chunk_key": "chunk-1",
            "content": "Demo > Điều 1 > Thuế 1.",
            "content_sha256": "357303a997e14de6aa3e9b8603ac96241b9816c75e9a4bb0d49ab30703d06ab2",
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
              "breadcrumb": "Demo > Điều 1"
            },
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": null,
            "title": "Demo",
            "source_url": null,
            "language": "vi",
            "issued_on": null,
            "effective_from": null,
            "effective_to": null,
            "effect_status_reported": null,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {}
          },
          {
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002",
            "source_document_id": "00000000-0000-0000-0000-00000000001e",
            "document_structure_id": "00000000-0000-0000-0000-000000000028",
            "chunk_key": "chunk-2",
            "content": "Demo > Điều 1 > Thuế 2.",
            "content_sha256": "dd9314bb58dd5dfa69a24b00571195f1ee0d4bd47d384e0486ed978396fef1c0",
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
              "breadcrumb": "Demo > Điều 1"
            },
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": null,
            "title": "Demo",
            "source_url": null,
            "language": "vi",
            "issued_on": null,
            "effective_from": null,
            "effective_to": null,
            "effect_status_reported": null,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {}
          }
        ],
        "warnings": [
          {
            "code": "SOURCE_URL_MISSING",
            "message": "Source URL is unavailable.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001"
          },
          {
            "code": "TEMPORAL_METADATA_INCOMPLETE",
            "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001"
          },
          {
            "code": "SOURCE_URL_MISSING",
            "message": "Source URL is unavailable.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002"
          },
          {
            "code": "TEMPORAL_METADATA_INCOMPLETE",
            "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002"
          }
        ],
        "error": null,
        "retrieved_at": "2026-11-21T15:06:50.758648Z",
        "consistency": "BEST_EFFORT"
      },
      {
        "schema_version": "1",
        "request_id": "0df27954-c4f5-4b94-8e77-a2a5eca7344a",
        "query": "hợp đồng",
        "query_used": "hợp đồng",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ],
        "selected_index_name": "vbpl-bm25-unicode-v1",
        "index": {
          "id": "00000000-0000-0000-0000-000000000014",
          "index_name": "vbpl-bm25-unicode-v1",
          "index_version": "v1",
          "status": "READY",
          "updated_at": "2026-11-10T00:00:00Z",
          "algorithm": "BM25",
          "tokenizer": "unicode-nfc-lower-v1"
        },
        "status": "OK",
        "evidence": [
          {
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001",
            "source_document_id": "00000000-0000-0000-0000-00000000001e",
            "document_structure_id": "00000000-0000-0000-0000-000000000028",
            "chunk_key": "chunk-1",
            "content": "Demo > Điều 1 > Thuế 1.",
            "content_sha256": "357303a997e14de6aa3e9b8603ac96241b9816c75e9a4bb0d49ab30703d06ab2",
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
              "breadcrumb": "Demo > Điều 1"
            },
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": null,
            "title": "Demo",
            "source_url": null,
            "language": "vi",
            "issued_on": null,
            "effective_from": null,
            "effective_to": null,
            "effect_status_reported": null,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {}
          },
          {
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002",
            "source_document_id": "00000000-0000-0000-0000-00000000001e",
            "document_structure_id": "00000000-0000-0000-0000-000000000028",
            "chunk_key": "chunk-2",
            "content": "Demo > Điều 1 > Thuế 2.",
            "content_sha256": "dd9314bb58dd5dfa69a24b00571195f1ee0d4bd47d384e0486ed978396fef1c0",
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
              "breadcrumb": "Demo > Điều 1"
            },
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": null,
            "title": "Demo",
            "source_url": null,
            "language": "vi",
            "issued_on": null,
            "effective_from": null,
            "effective_to": null,
            "effect_status_reported": null,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {}
          }
        ],
        "warnings": [
          {
            "code": "SOURCE_URL_MISSING",
            "message": "Source URL is unavailable.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001"
          },
          {
            "code": "TEMPORAL_METADATA_INCOMPLETE",
            "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001"
          },
          {
            "code": "SOURCE_URL_MISSING",
            "message": "Source URL is unavailable.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002"
          },
          {
            "code": "TEMPORAL_METADATA_INCOMPLETE",
            "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002"
          }
        ],
        "error": null,
        "retrieved_at": "2026-11-21T15:06:50.758648Z",
        "consistency": "BEST_EFFORT"
      },
      {
        "schema_version": "1",
        "request_id": "c6e4bbd1-7db9-4c3a-a4ab-be9dc3e343d6",
        "query": "bảo hiểm",
        "query_used": "bảo hiểm",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ],
        "selected_index_name": "vbpl-bm25-unicode-v1",
        "index": {
          "id": "00000000-0000-0000-0000-000000000014",
          "index_name": "vbpl-bm25-unicode-v1",
          "index_version": "v1",
          "status": "READY",
          "updated_at": "2026-11-10T00:00:00Z",
          "algorithm": "BM25",
          "tokenizer": "unicode-nfc-lower-v1"
        },
        "status": "OK",
        "evidence": [
          {
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001",
            "source_document_id": "00000000-0000-0000-0000-00000000001e",
            "document_structure_id": "00000000-0000-0000-0000-000000000028",
            "chunk_key": "chunk-1",
            "content": "Demo > Điều 1 > Thuế 1.",
            "content_sha256": "357303a997e14de6aa3e9b8603ac96241b9816c75e9a4bb0d49ab30703d06ab2",
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
              "breadcrumb": "Demo > Điều 1"
            },
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": null,
            "title": "Demo",
            "source_url": null,
            "language": "vi",
            "issued_on": null,
            "effective_from": null,
            "effective_to": null,
            "effect_status_reported": null,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {}
          },
          {
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002",
            "source_document_id": "00000000-0000-0000-0000-00000000001e",
            "document_structure_id": "00000000-0000-0000-0000-000000000028",
            "chunk_key": "chunk-2",
            "content": "Demo > Điều 1 > Thuế 2.",
            "content_sha256": "dd9314bb58dd5dfa69a24b00571195f1ee0d4bd47d384e0486ed978396fef1c0",
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
              "breadcrumb": "Demo > Điều 1"
            },
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": null,
            "title": "Demo",
            "source_url": null,
            "language": "vi",
            "issued_on": null,
            "effective_from": null,
            "effective_to": null,
            "effect_status_reported": null,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {}
          }
        ],
        "warnings": [
          {
            "code": "SOURCE_URL_MISSING",
            "message": "Source URL is unavailable.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001"
          },
          {
            "code": "TEMPORAL_METADATA_INCOMPLETE",
            "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001"
          },
          {
            "code": "SOURCE_URL_MISSING",
            "message": "Source URL is unavailable.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002"
          },
          {
            "code": "TEMPORAL_METADATA_INCOMPLETE",
            "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002"
          }
        ],
        "error": null,
        "retrieved_at": "2026-11-21T15:06:50.758648Z",
        "consistency": "BEST_EFFORT"
      }
    ],
    "status": "COMPLETED"
  }
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "response_types": [
    "RetrievalResponse",
    "RetrievalResponse",
    "RetrievalResponse"
  ],
  "plan_identity_preserved": true,
  "plan_unchanged": true,
  "response_identity_preserved": true,
  "max_active_calls": 1,
  "evidence_payload_hashes_match": true,
  "handoff_warning_codes": [
    "SOURCE_URL_MISSING",
    "TEMPORAL_METADATA_INCOMPLETE",
    "SOURCE_URL_MISSING",
    "TEMPORAL_METADATA_INCOMPLETE",
    "SOURCE_URL_MISSING",
    "TEMPORAL_METADATA_INCOMPLETE",
    "SOURCE_URL_MISSING",
    "TEMPORAL_METADATA_INCOMPLETE",
    "SOURCE_URL_MISSING",
    "TEMPORAL_METADATA_INCOMPLETE",
    "SOURCE_URL_MISSING",
    "TEMPORAL_METADATA_INCOMPLETE"
  ],
  "handoff_error_codes": [],
  "handoff_roundtrip_equal": true,
  "handoff_roundtrip_types": [
    "RetrievalResponse",
    "RetrievalResponse",
    "RetrievalResponse"
  ],
  "handoff_projection": {
    "schema_version": "1",
    "question": "thuế; hợp đồng; bảo hiểm",
    "request_id": "fixture-request",
    "run_id": "fixture-run",
    "options": {
      "mode": "bm25",
      "top_k": 2,
      "as_of_date": "2026-11-10",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ]
    },
    "search_status": "COMPLETED",
    "status": "READY"
  },
  "handoff_full_payload": "See search-traces.json/search_traces/multi_success/handoff"
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[
  {
    "line_about_to_execute": 42,
    "request_count": null,
    "responses_accumulated": null
  },
  {
    "line_about_to_execute": 46,
    "request_count": 3,
    "responses_accumulated": 0
  },
  {
    "line_about_to_execute": 49,
    "request_count": 3,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 46,
    "request_count": 3,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 49,
    "request_count": 3,
    "responses_accumulated": 2
  },
  {
    "line_about_to_execute": 46,
    "request_count": 3,
    "responses_accumulated": 2
  },
  {
    "line_about_to_execute": 49,
    "request_count": 3,
    "responses_accumulated": 3
  },
  {
    "line_about_to_execute": 46,
    "request_count": 3,
    "responses_accumulated": 3
  },
  {
    "line_about_to_execute": 56,
    "request_count": 3,
    "responses_accumulated": 3
  }
]
```

## 3. one_dense — OBSERVED

Real service dùng FakeEncoder / FakeDense, không tải/checkpoint hoặc inference E 5 thật. COSINE_SIMILARITY thuộc response service.

Backend: real RetrievalService with fake read/model ports.

```json
{
  "input_plan": {
    "original": "Trích dẫn: thuế",
    "intent": "quote_lookup",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "thuế",
        "purpose": "lookup"
      }
    ],
    "clarification": null
  },
  "options": {
    "mode": "dense",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "call_events": [
    {
      "event": "start",
      "number": 1,
      "query": "thuế"
    },
    {
      "event": "return",
      "number": 1,
      "status": "OK"
    }
  ],
  "search_state": {
    "plan": {
      "original": "Trích dẫn: thuế",
      "intent": "quote_lookup",
      "domain": "unknown",
      "temporal_scope": [],
      "subqueries": [
        {
          "text": "thuế",
          "purpose": "lookup"
        }
      ],
      "clarification": null
    },
    "requests": [
      {
        "query": "thuế",
        "mode": "dense",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ]
      }
    ],
    "responses": [
      {
        "schema_version": "1",
        "request_id": "2f64290e-c970-4e9c-823e-dfb5373dbac3",
        "query": "thuế",
        "query_used": "thuế",
        "mode": "dense",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ],
        "selected_index_name": "vbpl-multilingual-e5-small-v1",
        "index": {
          "id": "00000000-0000-0000-0000-00000000005a",
          "index_name": "vbpl-multilingual-e5-small-v1",
          "index_version": "v1",
          "status": "READY",
          "updated_at": "2026-11-10T00:00:00Z",
          "algorithm": null,
          "tokenizer": null
        },
        "status": "OK",
        "evidence": [
          {
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002",
            "source_document_id": "00000000-0000-0000-0000-00000000001e",
            "document_structure_id": "00000000-0000-0000-0000-000000000028",
            "chunk_key": "chunk-2",
            "content": "Demo > Điều 1 > Thuế 2.",
            "content_sha256": "dd9314bb58dd5dfa69a24b00571195f1ee0d4bd47d384e0486ed978396fef1c0",
            "hash_check": "MATCHED_STORED",
            "content_representation": "retrieval_chunk_content",
            "rank": 1,
            "raw_score": 0.85,
            "score_kind": "COSINE_SIMILARITY",
            "retrieval_method": "dense",
            "node_id": null,
            "block_id": null,
            "chunk_type": "text",
            "start_offset": null,
            "end_offset": null,
            "chunk_metadata": {
              "breadcrumb": "Demo > Điều 1"
            },
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": null,
            "title": "Demo",
            "source_url": null,
            "language": "vi",
            "issued_on": null,
            "effective_from": null,
            "effective_to": null,
            "effect_status_reported": null,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {}
          },
          {
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000003",
            "source_document_id": "00000000-0000-0000-0000-00000000001e",
            "document_structure_id": "00000000-0000-0000-0000-000000000028",
            "chunk_key": "chunk-3",
            "content": "Demo > Điều 1 > Thuế 3.",
            "content_sha256": "35cd53527fe8239ade93d8deea38dda11a72dc3152079957309f3d7a667cef4a",
            "hash_check": "MATCHED_STORED",
            "content_representation": "retrieval_chunk_content",
            "rank": 2,
            "raw_score": 0.8,
            "score_kind": "COSINE_SIMILARITY",
            "retrieval_method": "dense",
            "node_id": null,
            "block_id": null,
            "chunk_type": "text",
            "start_offset": null,
            "end_offset": null,
            "chunk_metadata": {
              "breadcrumb": "Demo > Điều 1"
            },
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": null,
            "title": "Demo",
            "source_url": null,
            "language": "vi",
            "issued_on": null,
            "effective_from": null,
            "effective_to": null,
            "effect_status_reported": null,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {}
          }
        ],
        "warnings": [
          {
            "code": "SOURCE_URL_MISSING",
            "message": "Source URL is unavailable.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002"
          },
          {
            "code": "TEMPORAL_METADATA_INCOMPLETE",
            "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002"
          },
          {
            "code": "SOURCE_URL_MISSING",
            "message": "Source URL is unavailable.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000003"
          },
          {
            "code": "TEMPORAL_METADATA_INCOMPLETE",
            "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000003"
          }
        ],
        "error": null,
        "retrieved_at": "2026-11-21T15:06:50.744124Z",
        "consistency": "BEST_EFFORT"
      }
    ],
    "status": "COMPLETED"
  }
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "response_types": [
    "RetrievalResponse"
  ],
  "plan_identity_preserved": true,
  "plan_unchanged": true,
  "response_identity_preserved": true,
  "max_active_calls": 1,
  "evidence_payload_hashes_match": true,
  "handoff_warning_codes": [
    "SOURCE_URL_MISSING",
    "TEMPORAL_METADATA_INCOMPLETE",
    "SOURCE_URL_MISSING",
    "TEMPORAL_METADATA_INCOMPLETE"
  ],
  "handoff_error_codes": [],
  "handoff_roundtrip_equal": true,
  "handoff_roundtrip_types": [
    "RetrievalResponse"
  ],
  "handoff_projection": {
    "schema_version": "1",
    "question": "Trích dẫn: thuế",
    "request_id": "fixture-request",
    "run_id": "fixture-run",
    "options": {
      "mode": "dense",
      "top_k": 2,
      "as_of_date": "2026-11-10",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ]
    },
    "search_status": "COMPLETED",
    "status": "READY"
  },
  "handoff_full_payload": "See search-traces.json/search_traces/one_dense/handoff"
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[
  {
    "line_about_to_execute": 42,
    "request_count": null,
    "responses_accumulated": null
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 0
  },
  {
    "line_about_to_execute": 49,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 56,
    "request_count": 1,
    "responses_accumulated": 1
  }
]
```

## 4. one_hybrid — OBSERVED

Service helper chạy branches/fusion với fake ports; Search chỉ nhận HybridRetrievalResponse. Fusion metadata còn nguyên.

Backend: real RetrievalService with fake read/model ports.

```json
{
  "input_plan": {
    "original": "Trích dẫn: thuế",
    "intent": "quote_lookup",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "thuế",
        "purpose": "lookup"
      }
    ],
    "clarification": null
  },
  "options": {
    "mode": "hybrid",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "call_events": [
    {
      "event": "start",
      "number": 1,
      "query": "thuế"
    },
    {
      "event": "return",
      "number": 1,
      "status": "OK"
    }
  ],
  "search_state": {
    "plan": {
      "original": "Trích dẫn: thuế",
      "intent": "quote_lookup",
      "domain": "unknown",
      "temporal_scope": [],
      "subqueries": [
        {
          "text": "thuế",
          "purpose": "lookup"
        }
      ],
      "clarification": null
    },
    "requests": [
      {
        "query": "thuế",
        "mode": "hybrid",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ]
      }
    ],
    "responses": [
      {
        "schema_version": "1",
        "request_id": "203de3e2-519f-4738-9b6b-3e834e926c37",
        "query": "thuế",
        "query_used": "thuế",
        "mode": "hybrid",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ],
        "selected_index_name": "hybrid",
        "index": null,
        "status": "OK",
        "evidence": [
          {
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002",
            "source_document_id": "00000000-0000-0000-0000-00000000001e",
            "document_structure_id": "00000000-0000-0000-0000-000000000028",
            "chunk_key": "chunk-2",
            "content": "Demo > Điều 1 > Thuế 2.",
            "content_sha256": "dd9314bb58dd5dfa69a24b00571195f1ee0d4bd47d384e0486ed978396fef1c0",
            "hash_check": "MATCHED_STORED",
            "content_representation": "retrieval_chunk_content",
            "rank": 1,
            "raw_score": 0.03252247488101534,
            "score_kind": "RRF",
            "retrieval_method": "hybrid",
            "node_id": null,
            "block_id": null,
            "chunk_type": "text",
            "start_offset": null,
            "end_offset": null,
            "chunk_metadata": {
              "breadcrumb": "Demo > Điều 1"
            },
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": null,
            "title": "Demo",
            "source_url": null,
            "language": "vi",
            "issued_on": null,
            "effective_from": null,
            "effective_to": null,
            "effect_status_reported": null,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {}
          },
          {
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001",
            "source_document_id": "00000000-0000-0000-0000-00000000001e",
            "document_structure_id": "00000000-0000-0000-0000-000000000028",
            "chunk_key": "chunk-1",
            "content": "Demo > Điều 1 > Thuế 1.",
            "content_sha256": "357303a997e14de6aa3e9b8603ac96241b9816c75e9a4bb0d49ab30703d06ab2",
            "hash_check": "MATCHED_STORED",
            "content_representation": "retrieval_chunk_content",
            "rank": 2,
            "raw_score": 0.01639344262295082,
            "score_kind": "RRF",
            "retrieval_method": "hybrid",
            "node_id": null,
            "block_id": null,
            "chunk_type": "text",
            "start_offset": null,
            "end_offset": null,
            "chunk_metadata": {
              "breadcrumb": "Demo > Điều 1"
            },
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": null,
            "title": "Demo",
            "source_url": null,
            "language": "vi",
            "issued_on": null,
            "effective_from": null,
            "effective_to": null,
            "effect_status_reported": null,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {}
          }
        ],
        "warnings": [
          {
            "code": "SOURCE_URL_MISSING",
            "message": "Source URL is unavailable.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001"
          },
          {
            "code": "TEMPORAL_METADATA_INCOMPLETE",
            "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001"
          },
          {
            "code": "SOURCE_URL_MISSING",
            "message": "Source URL is unavailable.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002"
          },
          {
            "code": "TEMPORAL_METADATA_INCOMPLETE",
            "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002"
          }
        ],
        "error": null,
        "retrieved_at": "2026-11-21T15:06:50.744124Z",
        "consistency": "BEST_EFFORT",
        "fusion": {
          "algorithm": "RRF",
          "failure_policy": "STRICT",
          "execution": "SEQUENTIAL",
          "config": {
            "rrf_k": 60,
            "bm25_candidates": 20,
            "dense_candidates": 20
          },
          "branches": [
            {
              "backend": "bm25",
              "status": "OK",
              "requested_candidates": 20,
              "returned_candidates": 2,
              "index": {
                "id": "00000000-0000-0000-0000-000000000014",
                "index_name": "vbpl-bm25-unicode-v1",
                "index_version": "v1",
                "status": "READY",
                "updated_at": "2026-11-10T00:00:00Z",
                "algorithm": "BM25",
                "tokenizer": "unicode-nfc-lower-v1"
              },
              "error": null
            },
            {
              "backend": "dense",
              "status": "OK",
              "requested_candidates": 20,
              "returned_candidates": 2,
              "index": {
                "id": "00000000-0000-0000-0000-00000000005a",
                "index_name": "vbpl-multilingual-e5-small-v1",
                "index_version": "v1",
                "status": "READY",
                "updated_at": "2026-11-10T00:00:00Z",
                "algorithm": null,
                "tokenizer": null
              },
              "error": null
            }
          ],
          "ranking": [
            {
              "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002",
              "contributions": [
                {
                  "backend": "bm25",
                  "rank": 2,
                  "raw_score": 5.4,
                  "score_kind": "BM25"
                },
                {
                  "backend": "dense",
                  "rank": 1,
                  "raw_score": 0.85,
                  "score_kind": "COSINE_SIMILARITY"
                }
              ]
            },
            {
              "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001",
              "contributions": [
                {
                  "backend": "bm25",
                  "rank": 1,
                  "raw_score": 7.2,
                  "score_kind": "BM25"
                }
              ]
            }
          ]
        }
      }
    ],
    "status": "COMPLETED"
  }
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "response_types": [
    "HybridRetrievalResponse"
  ],
  "plan_identity_preserved": true,
  "plan_unchanged": true,
  "response_identity_preserved": true,
  "max_active_calls": 1,
  "evidence_payload_hashes_match": true,
  "handoff_warning_codes": [
    "SOURCE_URL_MISSING",
    "TEMPORAL_METADATA_INCOMPLETE",
    "SOURCE_URL_MISSING",
    "TEMPORAL_METADATA_INCOMPLETE"
  ],
  "handoff_error_codes": [],
  "handoff_roundtrip_equal": true,
  "handoff_roundtrip_types": [
    "HybridRetrievalResponse"
  ],
  "handoff_projection": {
    "schema_version": "1",
    "question": "Trích dẫn: thuế",
    "request_id": "fixture-request",
    "run_id": "fixture-run",
    "options": {
      "mode": "hybrid",
      "top_k": 2,
      "as_of_date": "2026-11-10",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ]
    },
    "search_status": "COMPLETED",
    "status": "READY"
  },
  "handoff_full_payload": "See search-traces.json/search_traces/one_hybrid/handoff"
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[
  {
    "line_about_to_execute": 42,
    "request_count": null,
    "responses_accumulated": null
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 0
  },
  {
    "line_about_to_execute": 49,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 56,
    "request_count": 1,
    "responses_accumulated": 1
  }
]
```

## 5. one_rerank — OBSERVED

Real service + fake scorer trả RerankedHybridRetrievalResponse /reranking APPLIED. APPLIED ở fixture không phải local model inference mới.

Backend: real RetrievalService with fake read/model ports.

```json
{
  "input_plan": {
    "original": "Trích dẫn: thuế",
    "intent": "quote_lookup",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "thuế",
        "purpose": "lookup"
      }
    ],
    "clarification": null
  },
  "options": {
    "mode": "hybrid",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "call_events": [
    {
      "event": "start",
      "number": 1,
      "query": "thuế"
    },
    {
      "event": "return",
      "number": 1,
      "status": "OK"
    }
  ],
  "search_state": {
    "plan": {
      "original": "Trích dẫn: thuế",
      "intent": "quote_lookup",
      "domain": "unknown",
      "temporal_scope": [],
      "subqueries": [
        {
          "text": "thuế",
          "purpose": "lookup"
        }
      ],
      "clarification": null
    },
    "requests": [
      {
        "query": "thuế",
        "mode": "hybrid",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ]
      }
    ],
    "responses": [
      {
        "schema_version": "1",
        "request_id": "d0fa4a67-98e3-42c5-8119-07977020d558",
        "query": "thuế",
        "query_used": "thuế",
        "mode": "hybrid",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ],
        "selected_index_name": "hybrid",
        "index": null,
        "status": "OK",
        "evidence": [
          {
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000003",
            "source_document_id": "00000000-0000-0000-0000-00000000001e",
            "document_structure_id": "00000000-0000-0000-0000-000000000028",
            "chunk_key": "chunk-3",
            "content": "Demo > Điều 1 > Thuế 3.",
            "content_sha256": "35cd53527fe8239ade93d8deea38dda11a72dc3152079957309f3d7a667cef4a",
            "hash_check": "MATCHED_STORED",
            "content_representation": "retrieval_chunk_content",
            "rank": 1,
            "raw_score": 0.016129032258064516,
            "score_kind": "RRF",
            "retrieval_method": "hybrid",
            "node_id": null,
            "block_id": null,
            "chunk_type": "text",
            "start_offset": null,
            "end_offset": null,
            "chunk_metadata": {
              "breadcrumb": "Demo > Điều 1"
            },
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": null,
            "title": "Demo",
            "source_url": null,
            "language": "vi",
            "issued_on": null,
            "effective_from": null,
            "effective_to": null,
            "effect_status_reported": null,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {}
          },
          {
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001",
            "source_document_id": "00000000-0000-0000-0000-00000000001e",
            "document_structure_id": "00000000-0000-0000-0000-000000000028",
            "chunk_key": "chunk-1",
            "content": "Demo > Điều 1 > Thuế 1.",
            "content_sha256": "357303a997e14de6aa3e9b8603ac96241b9816c75e9a4bb0d49ab30703d06ab2",
            "hash_check": "MATCHED_STORED",
            "content_representation": "retrieval_chunk_content",
            "rank": 2,
            "raw_score": 0.01639344262295082,
            "score_kind": "RRF",
            "retrieval_method": "hybrid",
            "node_id": null,
            "block_id": null,
            "chunk_type": "text",
            "start_offset": null,
            "end_offset": null,
            "chunk_metadata": {
              "breadcrumb": "Demo > Điều 1"
            },
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": null,
            "title": "Demo",
            "source_url": null,
            "language": "vi",
            "issued_on": null,
            "effective_from": null,
            "effective_to": null,
            "effect_status_reported": null,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {}
          }
        ],
        "warnings": [
          {
            "code": "SOURCE_URL_MISSING",
            "message": "Source URL is unavailable.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001"
          },
          {
            "code": "TEMPORAL_METADATA_INCOMPLETE",
            "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001"
          },
          {
            "code": "SOURCE_URL_MISSING",
            "message": "Source URL is unavailable.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000003"
          },
          {
            "code": "TEMPORAL_METADATA_INCOMPLETE",
            "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000003"
          }
        ],
        "error": null,
        "retrieved_at": "2026-11-21T15:06:50.758648Z",
        "consistency": "BEST_EFFORT",
        "fusion": {
          "algorithm": "RRF",
          "failure_policy": "STRICT",
          "execution": "SEQUENTIAL",
          "config": {
            "rrf_k": 60,
            "bm25_candidates": 20,
            "dense_candidates": 20
          },
          "branches": [
            {
              "backend": "bm25",
              "status": "OK",
              "requested_candidates": 20,
              "returned_candidates": 2,
              "index": {
                "id": "00000000-0000-0000-0000-000000000014",
                "index_name": "vbpl-bm25-unicode-v1",
                "index_version": "v1",
                "status": "READY",
                "updated_at": "2026-11-10T00:00:00Z",
                "algorithm": "BM25",
                "tokenizer": "unicode-nfc-lower-v1"
              },
              "error": null
            },
            {
              "backend": "dense",
              "status": "OK",
              "requested_candidates": 20,
              "returned_candidates": 2,
              "index": {
                "id": "00000000-0000-0000-0000-00000000005a",
                "index_name": "vbpl-multilingual-e5-small-v1",
                "index_version": "v1",
                "status": "READY",
                "updated_at": "2026-11-10T00:00:00Z",
                "algorithm": null,
                "tokenizer": null
              },
              "error": null
            }
          ],
          "ranking": [
            {
              "retrieval_chunk_id": "00000000-0000-0000-0000-000000000003",
              "contributions": [
                {
                  "backend": "dense",
                  "rank": 2,
                  "raw_score": 0.8,
                  "score_kind": "COSINE_SIMILARITY"
                }
              ]
            },
            {
              "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001",
              "contributions": [
                {
                  "backend": "bm25",
                  "rank": 1,
                  "raw_score": 7.2,
                  "score_kind": "BM25"
                }
              ]
            }
          ]
        },
        "reranking": {
          "schema_version": "1",
          "status": "APPLIED",
          "model_name": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
          "model_revision": "1427fd652930e4ba29e8149678df786c240d8825",
          "config": {
            "enabled": true,
            "model_path": null,
            "candidate_pool": 20,
            "batch_size": 4,
            "max_length": 512,
            "inference_timeout_seconds": 10.0,
            "total_timeout_seconds": 40.0
          },
          "requested_candidates": 20,
          "candidates": [
            {
              "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002",
              "original_rank": 1,
              "rrf_score": 0.03252247488101534,
              "cross_encoder_score": 0.0,
              "final_rank": null
            },
            {
              "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001",
              "original_rank": 2,
              "rrf_score": 0.01639344262295082,
              "cross_encoder_score": 1.0,
              "final_rank": 2
            },
            {
              "retrieval_chunk_id": "00000000-0000-0000-0000-000000000003",
              "original_rank": 3,
              "rrf_score": 0.016129032258064516,
              "cross_encoder_score": 2.0,
              "final_rank": 1
            }
          ],
          "diagnostics": {
            "scores": [
              0.0,
              1.0,
              2.0
            ],
            "truncated": [
              false,
              false,
              false
            ],
            "cold": false,
            "load_seconds": 0.0,
            "inference_seconds": 0.0
          },
          "failure_code": null
        }
      }
    ],
    "status": "COMPLETED"
  }
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "response_types": [
    "RerankedHybridRetrievalResponse"
  ],
  "plan_identity_preserved": true,
  "plan_unchanged": true,
  "response_identity_preserved": true,
  "max_active_calls": 1,
  "evidence_payload_hashes_match": true,
  "handoff_warning_codes": [
    "SOURCE_URL_MISSING",
    "TEMPORAL_METADATA_INCOMPLETE",
    "SOURCE_URL_MISSING",
    "TEMPORAL_METADATA_INCOMPLETE"
  ],
  "handoff_error_codes": [],
  "handoff_roundtrip_equal": true,
  "handoff_roundtrip_types": [
    "RerankedHybridRetrievalResponse"
  ],
  "handoff_projection": {
    "schema_version": "1",
    "question": "Trích dẫn: thuế",
    "request_id": "fixture-request",
    "run_id": "fixture-run",
    "options": {
      "mode": "hybrid",
      "top_k": 2,
      "as_of_date": "2026-11-10",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ]
    },
    "search_status": "COMPLETED",
    "status": "READY"
  },
  "handoff_full_payload": "See search-traces.json/search_traces/one_rerank/handoff"
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[
  {
    "line_about_to_execute": 42,
    "request_count": null,
    "responses_accumulated": null
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 0
  },
  {
    "line_about_to_execute": 49,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 56,
    "request_count": 1,
    "responses_accumulated": 1
  }
]
```

## 6. clarification — OBSERVED

Valid plan vẫn có subquery nhưng guard trả empty requests/responses; 0 calls. Không gọi handoff builder ở harness cho case này.

Backend: synthetic service.

```json
{
  "input_plan": {
    "original": "Có được không?",
    "intent": "legal_question",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "Có được không",
        "purpose": "question_part"
      }
    ],
    "clarification": "Bạn cần tra cứu quy định hoặc tình huống cụ thể nào?"
  },
  "options": {
    "mode": "bm25",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "call_events": [],
  "search_state": {
    "plan": {
      "original": "Có được không?",
      "intent": "legal_question",
      "domain": "unknown",
      "temporal_scope": [],
      "subqueries": [
        {
          "text": "Có được không",
          "purpose": "question_part"
        }
      ],
      "clarification": "Bạn cần tra cứu quy định hoặc tình huống cụ thể nào?"
    },
    "requests": [],
    "responses": [],
    "status": "CLARIFICATION_REQUIRED"
  }
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "response_types": [],
  "plan_identity_preserved": true,
  "plan_unchanged": true,
  "response_identity_preserved": true,
  "max_active_calls": 0,
  "evidence_payload_hashes_match": true
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[
  {
    "line_about_to_execute": 42,
    "request_count": null,
    "responses_accumulated": null
  }
]
```

## 7. missing_plan — OBSERVED

Dict rỗng fail receiving QueryPlan trước options/requests/service. Không có SearchState được trả.

Backend: synthetic service.

```json
{
  "input_plan": {},
  "options": {
    "mode": "bm25",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "call_events": [],
  "exception": {
    "type": "ValidationError",
    "details": [
      {
        "type": "missing",
        "loc": [
          "original"
        ]
      },
      {
        "type": "missing",
        "loc": [
          "intent"
        ]
      },
      {
        "type": "missing",
        "loc": [
          "domain"
        ]
      },
      {
        "type": "missing",
        "loc": [
          "temporal_scope"
        ]
      },
      {
        "type": "missing",
        "loc": [
          "subqueries"
        ]
      },
      {
        "type": "missing",
        "loc": [
          "clarification"
        ]
      }
    ]
  },
  "requests_observed": [],
  "responses_observed": []
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "plan_unchanged": true,
  "max_active_calls": 0
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[]
```

## 8. empty_subqueries — OBSERVED

Plan có fields khác hợp lệ nhưng cardinality 0 bị reject; không gọi service.

Backend: synthetic service.

```json
{
  "input_plan": {
    "original": "thuế",
    "intent": "legal_question",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [],
    "clarification": null
  },
  "options": {
    "mode": "bm25",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "call_events": [],
  "exception": {
    "type": "ValidationError",
    "details": [
      {
        "type": "too_short",
        "loc": [
          "subqueries"
        ]
      }
    ]
  },
  "requests_observed": [],
  "responses_observed": []
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "plan_unchanged": true,
  "max_active_calls": 0
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[]
```

## 9. tab_second — OBSERVED

Subquery tab ở vị trí 2 qua QueryPlan min_length nhưng request nonblank fail. Tuple construction chưa hoàn tất nên 0 calls dù part đầu hợp lệ.

Backend: synthetic service.

```json
{
  "input_plan": {
    "original": "thuế; \t; hợp đồng",
    "intent": "legal_question",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "thuế",
        "purpose": "question_part"
      },
      {
        "text": "\t",
        "purpose": "question_part"
      },
      {
        "text": "hợp đồng",
        "purpose": "question_part"
      }
    ],
    "clarification": null
  },
  "options": {
    "mode": "bm25",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "call_events": [],
  "exception": {
    "type": "ValidationError",
    "details": [
      {
        "type": "value_error",
        "loc": [
          "query"
        ]
      }
    ]
  },
  "requests_observed": [],
  "responses_observed": []
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "plan_unchanged": true,
  "max_active_calls": 0
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[
  {
    "line_about_to_execute": 42,
    "request_count": null,
    "responses_accumulated": null
  }
]
```

## 10. no_match — OBSERVED

 NO_MATCH là native outcome hợp lệ; Search COMPLETED, harness handoff NO_MATCH, không phải invalid input.

Backend: synthetic service.

```json
{
  "input_plan": {
    "original": "thuế",
    "intent": "legal_question",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "thuế",
        "purpose": "question_part"
      }
    ],
    "clarification": null
  },
  "options": {
    "mode": "bm25",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "call_events": [
    {
      "event": "start",
      "number": 1,
      "query": "thuế"
    },
    {
      "event": "return",
      "number": 1,
      "status": "NO_MATCH"
    }
  ],
  "search_state": {
    "plan": {
      "original": "thuế",
      "intent": "legal_question",
      "domain": "unknown",
      "temporal_scope": [],
      "subqueries": [
        {
          "text": "thuế",
          "purpose": "question_part"
        }
      ],
      "clarification": null
    },
    "requests": [
      {
        "query": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ]
      }
    ],
    "responses": [
      {
        "schema_version": "1",
        "request_id": "00000000-0000-0000-0000-000000000001",
        "query": "thuế",
        "query_used": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ],
        "selected_index_name": "synthetic-fixture",
        "index": null,
        "status": "NO_MATCH",
        "evidence": [],
        "warnings": [
          {
            "code": "FIXTURE_WARNING",
            "message": "Synthetic observation",
            "retrieval_chunk_id": null
          }
        ],
        "error": null,
        "retrieved_at": "2026-11-21T00:00:00Z",
        "consistency": "BEST_EFFORT"
      }
    ],
    "status": "COMPLETED"
  }
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "response_types": [
    "RetrievalResponse"
  ],
  "plan_identity_preserved": true,
  "plan_unchanged": true,
  "response_identity_preserved": true,
  "max_active_calls": 1,
  "evidence_payload_hashes_match": true,
  "handoff_warning_codes": [
    "FIXTURE_WARNING"
  ],
  "handoff_error_codes": [],
  "handoff_roundtrip_equal": true,
  "handoff_roundtrip_types": [
    "RetrievalResponse"
  ],
  "handoff_projection": {
    "schema_version": "1",
    "question": "thuế",
    "request_id": "fixture-request",
    "run_id": "fixture-run",
    "options": {
      "mode": "bm25",
      "top_k": 2,
      "as_of_date": "2026-11-10",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ]
    },
    "search_status": "COMPLETED",
    "status": "NO_MATCH"
  },
  "handoff_full_payload": "See search-traces.json/search_traces/no_match/handoff"
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[
  {
    "line_about_to_execute": 42,
    "request_count": null,
    "responses_accumulated": null
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 0
  },
  {
    "line_about_to_execute": 49,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 56,
    "request_count": 1,
    "responses_accumulated": 1
  }
]
```

## 11. failed_first — OBSERVED

Call 1 classified FAILED được append trước return; requests prefix chỉ 1; call 2/3 không chạy.

Backend: synthetic service.

```json
{
  "input_plan": {
    "original": "thuế; hợp đồng; bảo hiểm",
    "intent": "legal_question",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "thuế",
        "purpose": "question_part"
      },
      {
        "text": "hợp đồng",
        "purpose": "question_part"
      },
      {
        "text": "bảo hiểm",
        "purpose": "question_part"
      }
    ],
    "clarification": null
  },
  "options": {
    "mode": "bm25",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "call_events": [
    {
      "event": "start",
      "number": 1,
      "query": "thuế"
    },
    {
      "event": "return",
      "number": 1,
      "status": "FAILED"
    }
  ],
  "search_state": {
    "plan": {
      "original": "thuế; hợp đồng; bảo hiểm",
      "intent": "legal_question",
      "domain": "unknown",
      "temporal_scope": [],
      "subqueries": [
        {
          "text": "thuế",
          "purpose": "question_part"
        },
        {
          "text": "hợp đồng",
          "purpose": "question_part"
        },
        {
          "text": "bảo hiểm",
          "purpose": "question_part"
        }
      ],
      "clarification": null
    },
    "requests": [
      {
        "query": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ]
      }
    ],
    "responses": [
      {
        "schema_version": "1",
        "request_id": "00000000-0000-0000-0000-000000000001",
        "query": "thuế",
        "query_used": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ],
        "selected_index_name": "synthetic-fixture",
        "index": null,
        "status": "FAILED",
        "evidence": [],
        "warnings": [
          {
            "code": "FIXTURE_WARNING",
            "message": "Synthetic observation",
            "retrieval_chunk_id": null
          }
        ],
        "error": {
          "category": "DATABASE_FAILURE",
          "code": "FIXTURE_FAILURE",
          "stage": "search",
          "message": "Synthetic failure",
          "retryable": false
        },
        "retrieved_at": "2026-11-21T00:00:00Z",
        "consistency": "BEST_EFFORT"
      }
    ],
    "status": "FAILED"
  }
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "response_types": [
    "RetrievalResponse"
  ],
  "plan_identity_preserved": true,
  "plan_unchanged": true,
  "response_identity_preserved": true,
  "max_active_calls": 1,
  "evidence_payload_hashes_match": true,
  "handoff_warning_codes": [
    "FIXTURE_WARNING"
  ],
  "handoff_error_codes": [
    "FIXTURE_FAILURE"
  ],
  "handoff_roundtrip_equal": true,
  "handoff_roundtrip_types": [
    "RetrievalResponse"
  ],
  "handoff_projection": {
    "schema_version": "1",
    "question": "thuế; hợp đồng; bảo hiểm",
    "request_id": "fixture-request",
    "run_id": "fixture-run",
    "options": {
      "mode": "bm25",
      "top_k": 2,
      "as_of_date": "2026-11-10",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ]
    },
    "search_status": "FAILED",
    "status": "RETRIEVAL_FAILED"
  },
  "handoff_full_payload": "See search-traces.json/search_traces/failed_first/handoff"
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[
  {
    "line_about_to_execute": 42,
    "request_count": null,
    "responses_accumulated": null
  },
  {
    "line_about_to_execute": 46,
    "request_count": 3,
    "responses_accumulated": 0
  },
  {
    "line_about_to_execute": 49,
    "request_count": 3,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 50,
    "request_count": 3,
    "responses_accumulated": 1
  }
]
```

## 12. partial_failure — OBSERVED

Call 1 OK còn 2 evidence, call 2 FAILED, call 3 không chạy. SearchState FAILED và handoff RETRIEVAL_FAILED vẫn giữ prior evidence/history.

Backend: real RetrievalService with fake read/model ports.

```json
{
  "input_plan": {
    "original": "thuế; hợp đồng; bảo hiểm",
    "intent": "legal_question",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "thuế",
        "purpose": "question_part"
      },
      {
        "text": "hợp đồng",
        "purpose": "question_part"
      },
      {
        "text": "bảo hiểm",
        "purpose": "question_part"
      }
    ],
    "clarification": null
  },
  "options": {
    "mode": "bm25",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "call_events": [
    {
      "event": "start",
      "number": 1,
      "query": "thuế"
    },
    {
      "event": "return",
      "number": 1,
      "status": "OK"
    },
    {
      "event": "start",
      "number": 2,
      "query": "hợp đồng"
    },
    {
      "event": "return",
      "number": 2,
      "status": "FAILED"
    }
  ],
  "search_state": {
    "plan": {
      "original": "thuế; hợp đồng; bảo hiểm",
      "intent": "legal_question",
      "domain": "unknown",
      "temporal_scope": [],
      "subqueries": [
        {
          "text": "thuế",
          "purpose": "question_part"
        },
        {
          "text": "hợp đồng",
          "purpose": "question_part"
        },
        {
          "text": "bảo hiểm",
          "purpose": "question_part"
        }
      ],
      "clarification": null
    },
    "requests": [
      {
        "query": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ]
      },
      {
        "query": "hợp đồng",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ]
      }
    ],
    "responses": [
      {
        "schema_version": "1",
        "request_id": "9f170e4f-ca77-4b6f-a82a-f8521bd9f5e1",
        "query": "thuế",
        "query_used": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ],
        "selected_index_name": "vbpl-bm25-unicode-v1",
        "index": {
          "id": "00000000-0000-0000-0000-000000000014",
          "index_name": "vbpl-bm25-unicode-v1",
          "index_version": "v1",
          "status": "READY",
          "updated_at": "2026-11-10T00:00:00Z",
          "algorithm": "BM25",
          "tokenizer": "unicode-nfc-lower-v1"
        },
        "status": "OK",
        "evidence": [
          {
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001",
            "source_document_id": "00000000-0000-0000-0000-00000000001e",
            "document_structure_id": "00000000-0000-0000-0000-000000000028",
            "chunk_key": "chunk-1",
            "content": "Demo > Điều 1 > Thuế 1.",
            "content_sha256": "357303a997e14de6aa3e9b8603ac96241b9816c75e9a4bb0d49ab30703d06ab2",
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
              "breadcrumb": "Demo > Điều 1"
            },
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": null,
            "title": "Demo",
            "source_url": null,
            "language": "vi",
            "issued_on": null,
            "effective_from": null,
            "effective_to": null,
            "effect_status_reported": null,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {}
          },
          {
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002",
            "source_document_id": "00000000-0000-0000-0000-00000000001e",
            "document_structure_id": "00000000-0000-0000-0000-000000000028",
            "chunk_key": "chunk-2",
            "content": "Demo > Điều 1 > Thuế 2.",
            "content_sha256": "dd9314bb58dd5dfa69a24b00571195f1ee0d4bd47d384e0486ed978396fef1c0",
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
              "breadcrumb": "Demo > Điều 1"
            },
            "source_id": "vbpl",
            "source_record_id": "demo",
            "source_snapshot_id": null,
            "title": "Demo",
            "source_url": null,
            "language": "vi",
            "issued_on": null,
            "effective_from": null,
            "effective_to": null,
            "effect_status_reported": null,
            "usage_policy": "EXPERIMENTAL_ONLY",
            "source_metadata": {}
          }
        ],
        "warnings": [
          {
            "code": "SOURCE_URL_MISSING",
            "message": "Source URL is unavailable.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001"
          },
          {
            "code": "TEMPORAL_METADATA_INCOMPLETE",
            "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001"
          },
          {
            "code": "SOURCE_URL_MISSING",
            "message": "Source URL is unavailable.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002"
          },
          {
            "code": "TEMPORAL_METADATA_INCOMPLETE",
            "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
            "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002"
          }
        ],
        "error": null,
        "retrieved_at": "2026-11-21T15:06:50.776376Z",
        "consistency": "BEST_EFFORT"
      },
      {
        "schema_version": "1",
        "request_id": "00000000-0000-0000-0000-000000000002",
        "query": "hợp đồng",
        "query_used": "hợp đồng",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ],
        "selected_index_name": "synthetic-fixture",
        "index": null,
        "status": "FAILED",
        "evidence": [],
        "warnings": [
          {
            "code": "FIXTURE_WARNING",
            "message": "Synthetic observation",
            "retrieval_chunk_id": null
          }
        ],
        "error": {
          "category": "DATABASE_FAILURE",
          "code": "FIXTURE_FAILURE",
          "stage": "search",
          "message": "Synthetic failure",
          "retryable": false
        },
        "retrieved_at": "2026-11-21T00:00:00Z",
        "consistency": "BEST_EFFORT"
      }
    ],
    "status": "FAILED"
  }
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "response_types": [
    "RetrievalResponse",
    "RetrievalResponse"
  ],
  "plan_identity_preserved": true,
  "plan_unchanged": true,
  "response_identity_preserved": true,
  "max_active_calls": 1,
  "evidence_payload_hashes_match": true,
  "handoff_warning_codes": [
    "SOURCE_URL_MISSING",
    "TEMPORAL_METADATA_INCOMPLETE",
    "SOURCE_URL_MISSING",
    "TEMPORAL_METADATA_INCOMPLETE",
    "FIXTURE_WARNING"
  ],
  "handoff_error_codes": [
    "FIXTURE_FAILURE"
  ],
  "handoff_roundtrip_equal": true,
  "handoff_roundtrip_types": [
    "RetrievalResponse",
    "RetrievalResponse"
  ],
  "handoff_projection": {
    "schema_version": "1",
    "question": "thuế; hợp đồng; bảo hiểm",
    "request_id": "fixture-request",
    "run_id": "fixture-run",
    "options": {
      "mode": "bm25",
      "top_k": 2,
      "as_of_date": "2026-11-10",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ]
    },
    "search_status": "FAILED",
    "status": "RETRIEVAL_FAILED"
  },
  "handoff_full_payload": "See search-traces.json/search_traces/partial_failure/handoff"
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[
  {
    "line_about_to_execute": 42,
    "request_count": null,
    "responses_accumulated": null
  },
  {
    "line_about_to_execute": 46,
    "request_count": 3,
    "responses_accumulated": 0
  },
  {
    "line_about_to_execute": 49,
    "request_count": 3,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 46,
    "request_count": 3,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 49,
    "request_count": 3,
    "responses_accumulated": 2
  },
  {
    "line_about_to_execute": 50,
    "request_count": 3,
    "responses_accumulated": 2
  }
]
```

## 13. exception_second — OBSERVED

Call 2 raise RuntimeError; Search không return state. Recorder history chỉ là instrumentation observation, không output contract.

Backend: real RetrievalService with fake read/model ports.

```json
{
  "input_plan": {
    "original": "thuế; hợp đồng; bảo hiểm",
    "intent": "legal_question",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "thuế",
        "purpose": "question_part"
      },
      {
        "text": "hợp đồng",
        "purpose": "question_part"
      },
      {
        "text": "bảo hiểm",
        "purpose": "question_part"
      }
    ],
    "clarification": null
  },
  "options": {
    "mode": "bm25",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "call_events": [
    {
      "event": "start",
      "number": 1,
      "query": "thuế"
    },
    {
      "event": "return",
      "number": 1,
      "status": "OK"
    },
    {
      "event": "start",
      "number": 2,
      "query": "hợp đồng"
    }
  ],
  "exception": {
    "type": "RuntimeError",
    "message": "Synthetic dependency exception"
  },
  "requests_observed": [
    {
      "query": "thuế",
      "mode": "bm25",
      "top_k": 2,
      "as_of_date": "2026-11-10",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ]
    },
    {
      "query": "hợp đồng",
      "mode": "bm25",
      "top_k": 2,
      "as_of_date": "2026-11-10",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ]
    }
  ],
  "responses_observed": [
    {
      "schema_version": "1",
      "request_id": "7a472e6f-374e-45f2-9872-f592042fa176",
      "query": "thuế",
      "query_used": "thuế",
      "mode": "bm25",
      "top_k": 2,
      "as_of_date": "2026-11-10",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ],
      "selected_index_name": "vbpl-bm25-unicode-v1",
      "index": {
        "id": "00000000-0000-0000-0000-000000000014",
        "index_name": "vbpl-bm25-unicode-v1",
        "index_version": "v1",
        "status": "READY",
        "updated_at": "2026-11-10T00:00:00Z",
        "algorithm": "BM25",
        "tokenizer": "unicode-nfc-lower-v1"
      },
      "status": "OK",
      "evidence": [
        {
          "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001",
          "source_document_id": "00000000-0000-0000-0000-00000000001e",
          "document_structure_id": "00000000-0000-0000-0000-000000000028",
          "chunk_key": "chunk-1",
          "content": "Demo > Điều 1 > Thuế 1.",
          "content_sha256": "357303a997e14de6aa3e9b8603ac96241b9816c75e9a4bb0d49ab30703d06ab2",
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
            "breadcrumb": "Demo > Điều 1"
          },
          "source_id": "vbpl",
          "source_record_id": "demo",
          "source_snapshot_id": null,
          "title": "Demo",
          "source_url": null,
          "language": "vi",
          "issued_on": null,
          "effective_from": null,
          "effective_to": null,
          "effect_status_reported": null,
          "usage_policy": "EXPERIMENTAL_ONLY",
          "source_metadata": {}
        },
        {
          "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002",
          "source_document_id": "00000000-0000-0000-0000-00000000001e",
          "document_structure_id": "00000000-0000-0000-0000-000000000028",
          "chunk_key": "chunk-2",
          "content": "Demo > Điều 1 > Thuế 2.",
          "content_sha256": "dd9314bb58dd5dfa69a24b00571195f1ee0d4bd47d384e0486ed978396fef1c0",
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
            "breadcrumb": "Demo > Điều 1"
          },
          "source_id": "vbpl",
          "source_record_id": "demo",
          "source_snapshot_id": null,
          "title": "Demo",
          "source_url": null,
          "language": "vi",
          "issued_on": null,
          "effective_from": null,
          "effective_to": null,
          "effect_status_reported": null,
          "usage_policy": "EXPERIMENTAL_ONLY",
          "source_metadata": {}
        }
      ],
      "warnings": [
        {
          "code": "SOURCE_URL_MISSING",
          "message": "Source URL is unavailable.",
          "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001"
        },
        {
          "code": "TEMPORAL_METADATA_INCOMPLETE",
          "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
          "retrieval_chunk_id": "00000000-0000-0000-0000-000000000001"
        },
        {
          "code": "SOURCE_URL_MISSING",
          "message": "Source URL is unavailable.",
          "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002"
        },
        {
          "code": "TEMPORAL_METADATA_INCOMPLETE",
          "message": "Effective dates are partly unspecified; legal applicability has not been evaluated.",
          "retrieval_chunk_id": "00000000-0000-0000-0000-000000000002"
        }
      ],
      "error": null,
      "retrieved_at": "2026-11-21T15:06:50.790408Z",
      "consistency": "BEST_EFFORT"
    }
  ]
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "plan_unchanged": true,
  "max_active_calls": 1
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[
  {
    "line_about_to_execute": 42,
    "request_count": null,
    "responses_accumulated": null
  },
  {
    "line_about_to_execute": 46,
    "request_count": 3,
    "responses_accumulated": 0
  },
  {
    "line_about_to_execute": 49,
    "request_count": 3,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 46,
    "request_count": 3,
    "responses_accumulated": 1
  }
]
```

## 14. duplicate_calls — OBSERVED

Hai text thuế giống nhau tạo 2 service calls. Không Search -level cache/dedup.

Backend: synthetic service.

```json
{
  "input_plan": {
    "original": "thuế; thuế",
    "intent": "legal_question",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "thuế",
        "purpose": "question_part"
      },
      {
        "text": "thuế",
        "purpose": "question_part"
      }
    ],
    "clarification": null
  },
  "options": {
    "mode": "bm25",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "call_events": [
    {
      "event": "start",
      "number": 1,
      "query": "thuế"
    },
    {
      "event": "return",
      "number": 1,
      "status": "NO_MATCH"
    },
    {
      "event": "start",
      "number": 2,
      "query": "thuế"
    },
    {
      "event": "return",
      "number": 2,
      "status": "NO_MATCH"
    }
  ],
  "search_state": {
    "plan": {
      "original": "thuế; thuế",
      "intent": "legal_question",
      "domain": "unknown",
      "temporal_scope": [],
      "subqueries": [
        {
          "text": "thuế",
          "purpose": "question_part"
        },
        {
          "text": "thuế",
          "purpose": "question_part"
        }
      ],
      "clarification": null
    },
    "requests": [
      {
        "query": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ]
      },
      {
        "query": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ]
      }
    ],
    "responses": [
      {
        "schema_version": "1",
        "request_id": "00000000-0000-0000-0000-000000000001",
        "query": "thuế",
        "query_used": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ],
        "selected_index_name": "synthetic-fixture",
        "index": null,
        "status": "NO_MATCH",
        "evidence": [],
        "warnings": [
          {
            "code": "FIXTURE_WARNING",
            "message": "Synthetic observation",
            "retrieval_chunk_id": null
          }
        ],
        "error": null,
        "retrieved_at": "2026-11-21T00:00:00Z",
        "consistency": "BEST_EFFORT"
      },
      {
        "schema_version": "1",
        "request_id": "00000000-0000-0000-0000-000000000002",
        "query": "thuế",
        "query_used": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ],
        "selected_index_name": "synthetic-fixture",
        "index": null,
        "status": "NO_MATCH",
        "evidence": [],
        "warnings": [
          {
            "code": "FIXTURE_WARNING",
            "message": "Synthetic observation",
            "retrieval_chunk_id": null
          }
        ],
        "error": null,
        "retrieved_at": "2026-11-21T00:00:00Z",
        "consistency": "BEST_EFFORT"
      }
    ],
    "status": "COMPLETED"
  }
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "response_types": [
    "RetrievalResponse",
    "RetrievalResponse"
  ],
  "plan_identity_preserved": true,
  "plan_unchanged": true,
  "response_identity_preserved": true,
  "max_active_calls": 1,
  "evidence_payload_hashes_match": true,
  "handoff_warning_codes": [
    "FIXTURE_WARNING",
    "FIXTURE_WARNING"
  ],
  "handoff_error_codes": [],
  "handoff_roundtrip_equal": true,
  "handoff_roundtrip_types": [
    "RetrievalResponse",
    "RetrievalResponse"
  ],
  "handoff_projection": {
    "schema_version": "1",
    "question": "thuế; thuế",
    "request_id": "fixture-request",
    "run_id": "fixture-run",
    "options": {
      "mode": "bm25",
      "top_k": 2,
      "as_of_date": "2026-11-10",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ]
    },
    "search_status": "COMPLETED",
    "status": "NO_MATCH"
  },
  "handoff_full_payload": "See search-traces.json/search_traces/duplicate_calls/handoff"
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[
  {
    "line_about_to_execute": 42,
    "request_count": null,
    "responses_accumulated": null
  },
  {
    "line_about_to_execute": 46,
    "request_count": 2,
    "responses_accumulated": 0
  },
  {
    "line_about_to_execute": 49,
    "request_count": 2,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 46,
    "request_count": 2,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 49,
    "request_count": 2,
    "responses_accumulated": 2
  },
  {
    "line_about_to_execute": 46,
    "request_count": 2,
    "responses_accumulated": 2
  },
  {
    "line_about_to_execute": 56,
    "request_count": 2,
    "responses_accumulated": 2
  }
]
```

## 15. spaces_retained — OBSERVED

Request query giữ edge spaces, query_used strip theo dependency. Search không normalize text lần nữa.

Backend: synthetic service.

```json
{
  "input_plan": {
    "original": "  thuế  ",
    "intent": "legal_question",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "  thuế  ",
        "purpose": "question_part"
      }
    ],
    "clarification": null
  },
  "options": {
    "mode": "bm25",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "call_events": [
    {
      "event": "start",
      "number": 1,
      "query": "  thuế  "
    },
    {
      "event": "return",
      "number": 1,
      "status": "NO_MATCH"
    }
  ],
  "search_state": {
    "plan": {
      "original": "  thuế  ",
      "intent": "legal_question",
      "domain": "unknown",
      "temporal_scope": [],
      "subqueries": [
        {
          "text": "  thuế  ",
          "purpose": "question_part"
        }
      ],
      "clarification": null
    },
    "requests": [
      {
        "query": "  thuế  ",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ]
      }
    ],
    "responses": [
      {
        "schema_version": "1",
        "request_id": "00000000-0000-0000-0000-000000000001",
        "query": "  thuế  ",
        "query_used": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ],
        "selected_index_name": "synthetic-fixture",
        "index": null,
        "status": "NO_MATCH",
        "evidence": [],
        "warnings": [
          {
            "code": "FIXTURE_WARNING",
            "message": "Synthetic observation",
            "retrieval_chunk_id": null
          }
        ],
        "error": null,
        "retrieved_at": "2026-11-21T00:00:00Z",
        "consistency": "BEST_EFFORT"
      }
    ],
    "status": "COMPLETED"
  }
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "response_types": [
    "RetrievalResponse"
  ],
  "plan_identity_preserved": true,
  "plan_unchanged": true,
  "response_identity_preserved": true,
  "max_active_calls": 1,
  "evidence_payload_hashes_match": true,
  "handoff_warning_codes": [
    "FIXTURE_WARNING"
  ],
  "handoff_error_codes": [],
  "handoff_roundtrip_equal": true,
  "handoff_roundtrip_types": [
    "RetrievalResponse"
  ],
  "handoff_projection": {
    "schema_version": "1",
    "question": "  thuế  ",
    "request_id": "fixture-request",
    "run_id": "fixture-run",
    "options": {
      "mode": "bm25",
      "top_k": 2,
      "as_of_date": "2026-11-10",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ]
    },
    "search_status": "COMPLETED",
    "status": "NO_MATCH"
  },
  "handoff_full_payload": "See search-traces.json/search_traces/spaces_retained/handoff"
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[
  {
    "line_about_to_execute": 42,
    "request_count": null,
    "responses_accumulated": null
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 0
  },
  {
    "line_about_to_execute": 49,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 56,
    "request_count": 1,
    "responses_accumulated": 1
  }
]
```

## 16. context_mismatch — OBSERVED

Fake dependency cố tình trả query không khớp. Search giữ và COMPLETED; harness packet constructor reject. Không gán context check này cho Search.

Backend: synthetic service.

```json
{
  "input_plan": {
    "original": "thuế",
    "intent": "legal_question",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "thuế",
        "purpose": "question_part"
      }
    ],
    "clarification": null
  },
  "options": {
    "mode": "bm25",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "call_events": [
    {
      "event": "start",
      "number": 1,
      "query": "thuế"
    },
    {
      "event": "return",
      "number": 1,
      "status": "NO_MATCH"
    }
  ],
  "search_state": {
    "plan": {
      "original": "thuế",
      "intent": "legal_question",
      "domain": "unknown",
      "temporal_scope": [],
      "subqueries": [
        {
          "text": "thuế",
          "purpose": "question_part"
        }
      ],
      "clarification": null
    },
    "requests": [
      {
        "query": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ]
      }
    ],
    "responses": [
      {
        "schema_version": "1",
        "request_id": "00000000-0000-0000-0000-000000000001",
        "query": "different synthetic query",
        "query_used": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ],
        "selected_index_name": "synthetic-fixture",
        "index": null,
        "status": "NO_MATCH",
        "evidence": [],
        "warnings": [
          {
            "code": "FIXTURE_WARNING",
            "message": "Synthetic observation",
            "retrieval_chunk_id": null
          }
        ],
        "error": null,
        "retrieved_at": "2026-11-21T00:00:00Z",
        "consistency": "BEST_EFFORT"
      }
    ],
    "status": "COMPLETED"
  }
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "response_types": [
    "RetrievalResponse"
  ],
  "plan_identity_preserved": true,
  "plan_unchanged": true,
  "response_identity_preserved": true,
  "max_active_calls": 1,
  "evidence_payload_hashes_match": true,
  "handoff_exception": {
    "type": "ValidationError",
    "details": [
      {
        "type": "value_error",
        "loc": []
      }
    ]
  }
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[
  {
    "line_about_to_execute": 42,
    "request_count": null,
    "responses_accumulated": null
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 0
  },
  {
    "line_about_to_execute": 49,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 56,
    "request_count": 1,
    "responses_accumulated": 1
  }
]
```

## 17. extra_plan_field — OBSERVED

Parsed QueryPlan ignore confidence, raw SearchState.plan vẫn giữ. Packet.plan typed không có confidence. Không có confidence scoring.

Backend: synthetic service.

```json
{
  "input_plan": {
    "original": "thuế",
    "intent": "legal_question",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "thuế",
        "purpose": "question_part"
      }
    ],
    "clarification": null,
    "confidence": 0.99
  },
  "options": {
    "mode": "bm25",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "EXPERIMENTAL_ONLY"
    ]
  },
  "call_events": [
    {
      "event": "start",
      "number": 1,
      "query": "thuế"
    },
    {
      "event": "return",
      "number": 1,
      "status": "NO_MATCH"
    }
  ],
  "search_state": {
    "plan": {
      "original": "thuế",
      "intent": "legal_question",
      "domain": "unknown",
      "temporal_scope": [],
      "subqueries": [
        {
          "text": "thuế",
          "purpose": "question_part"
        }
      ],
      "clarification": null,
      "confidence": 0.99
    },
    "requests": [
      {
        "query": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ]
      }
    ],
    "responses": [
      {
        "schema_version": "1",
        "request_id": "00000000-0000-0000-0000-000000000001",
        "query": "thuế",
        "query_used": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "EXPERIMENTAL_ONLY"
        ],
        "selected_index_name": "synthetic-fixture",
        "index": null,
        "status": "NO_MATCH",
        "evidence": [],
        "warnings": [
          {
            "code": "FIXTURE_WARNING",
            "message": "Synthetic observation",
            "retrieval_chunk_id": null
          }
        ],
        "error": null,
        "retrieved_at": "2026-11-21T00:00:00Z",
        "consistency": "BEST_EFFORT"
      }
    ],
    "status": "COMPLETED"
  }
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "response_types": [
    "RetrievalResponse"
  ],
  "plan_identity_preserved": true,
  "plan_unchanged": true,
  "response_identity_preserved": true,
  "max_active_calls": 1,
  "evidence_payload_hashes_match": true,
  "handoff_warning_codes": [
    "FIXTURE_WARNING"
  ],
  "handoff_error_codes": [],
  "handoff_roundtrip_equal": true,
  "handoff_roundtrip_types": [
    "RetrievalResponse"
  ],
  "handoff_projection": {
    "schema_version": "1",
    "question": "thuế",
    "request_id": "fixture-request",
    "run_id": "fixture-run",
    "options": {
      "mode": "bm25",
      "top_k": 2,
      "as_of_date": "2026-11-10",
      "allowed_usage_policies": [
        "EXPERIMENTAL_ONLY"
      ]
    },
    "search_status": "COMPLETED",
    "status": "NO_MATCH"
  },
  "handoff_full_payload": "See search-traces.json/search_traces/extra_plan_field/handoff"
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[
  {
    "line_about_to_execute": 42,
    "request_count": null,
    "responses_accumulated": null
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 0
  },
  {
    "line_about_to_execute": 49,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 56,
    "request_count": 1,
    "responses_accumulated": 1
  }
]
```

## 18. normalized_options — OBSERVED

Date string và policy list đã được Pydantic validate thành date/tuple; strip/dedup policy observable trong requests. Đây là application option parsing, không user Query controls.

Backend: synthetic service.

```json
{
  "input_plan": {
    "original": "thuế",
    "intent": "legal_question",
    "domain": "unknown",
    "temporal_scope": [],
    "subqueries": [
      {
        "text": "thuế",
        "purpose": "question_part"
      }
    ],
    "clarification": null
  },
  "options": {
    "mode": "bm25",
    "top_k": 2,
    "as_of_date": "2026-11-10",
    "allowed_usage_policies": [
      "A",
      "B"
    ]
  },
  "call_events": [
    {
      "event": "start",
      "number": 1,
      "query": "thuế"
    },
    {
      "event": "return",
      "number": 1,
      "status": "NO_MATCH"
    }
  ],
  "search_state": {
    "plan": {
      "original": "thuế",
      "intent": "legal_question",
      "domain": "unknown",
      "temporal_scope": [],
      "subqueries": [
        {
          "text": "thuế",
          "purpose": "question_part"
        }
      ],
      "clarification": null
    },
    "requests": [
      {
        "query": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "A",
          "B"
        ]
      }
    ],
    "responses": [
      {
        "schema_version": "1",
        "request_id": "00000000-0000-0000-0000-000000000001",
        "query": "thuế",
        "query_used": "thuế",
        "mode": "bm25",
        "top_k": 2,
        "as_of_date": "2026-11-10",
        "allowed_usage_policies": [
          "A",
          "B"
        ],
        "selected_index_name": "synthetic-fixture",
        "index": null,
        "status": "NO_MATCH",
        "evidence": [],
        "warnings": [
          {
            "code": "FIXTURE_WARNING",
            "message": "Synthetic observation",
            "retrieval_chunk_id": null
          }
        ],
        "error": null,
        "retrieved_at": "2026-11-21T00:00:00Z",
        "consistency": "BEST_EFFORT"
      }
    ],
    "status": "COMPLETED"
  }
}
```

Kết quả identity/packet kiểm bằng harness (OBSERVED):

```json
{
  "response_types": [
    "RetrievalResponse"
  ],
  "plan_identity_preserved": true,
  "plan_unchanged": true,
  "response_identity_preserved": true,
  "max_active_calls": 1,
  "evidence_payload_hashes_match": true,
  "handoff_warning_codes": [
    "FIXTURE_WARNING"
  ],
  "handoff_error_codes": [],
  "handoff_roundtrip_equal": true,
  "handoff_roundtrip_types": [
    "RetrievalResponse"
  ],
  "handoff_projection": {
    "schema_version": "1",
    "question": "thuế",
    "request_id": "fixture-request",
    "run_id": "fixture-run",
    "options": {
      "mode": "bm25",
      "top_k": 2,
      "as_of_date": "2026-11-10",
      "allowed_usage_policies": [
        "A",
        "B"
      ]
    },
    "search_status": "COMPLETED",
    "status": "NO_MATCH"
  },
  "handoff_full_payload": "See search-traces.json/search_traces/normalized_options/handoff"
}
```

Local observations ở line events:giá trị là snapshot **trước statement ở dòng đó chạy**, không gán output sau statement nhầm thời điểm.

```json
[
  {
    "line_about_to_execute": 42,
    "request_count": null,
    "responses_accumulated": null
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 0
  },
  {
    "line_about_to_execute": 49,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 46,
    "request_count": 1,
    "responses_accumulated": 1
  },
  {
    "line_about_to_execute": 56,
    "request_count": 1,
    "responses_accumulated": 1
  }
]
```

## Bảng toàn bộ 35 direct Search cases

| Case | Calls | Search status/exception | Handoff do harness | Backend |
|---|---|---|---|---|
| one_bm25 | 1 | COMPLETED | READY | real RetrievalService with fake read/model ports |
| one_dense | 1 | COMPLETED | READY | real RetrievalService with fake read/model ports |
| one_hybrid | 1 | COMPLETED | READY | real RetrievalService with fake read/model ports |
| one_rerank | 1 | COMPLETED | READY | real RetrievalService with fake read/model ports |
| multi_success | 3 | COMPLETED | READY | real RetrievalService with fake read/model ports |
| duplicate_calls | 2 | COMPLETED | NO_MATCH | synthetic service |
| clarification | 0 | CLARIFICATION_REQUIRED | Không tạo | synthetic service |
| no_match | 1 | COMPLETED | NO_MATCH | synthetic service |
| failed_first | 1 | FAILED | RETRIEVAL_FAILED | synthetic service |
| partial_failure | 2 | FAILED | RETRIEVAL_FAILED | real RetrievalService with fake read/model ports |
| exception_second | 2 | RuntimeError | Không tạo | real RetrievalService with fake read/model ports |
| missing_plan | 0 | ValidationError | Không tạo | synthetic service |
| none_plan | 0 | ValidationError | Không tạo | synthetic service |
| empty_subqueries | 0 | ValidationError | Không tạo | synthetic service |
| empty_text | 0 | ValidationError | Không tạo | synthetic service |
| unsupported_intent | 0 | ValidationError | Không tạo | synthetic service |
| five_subqueries | 0 | ValidationError | Không tạo | synthetic service |
| clarification_invalid_plan | 0 | ValidationError | Không tạo | synthetic service |
| tab_second | 0 | ValidationError | Không tạo | synthetic service |
| spaces_retained | 1 | COMPLETED | NO_MATCH | synthetic service |
| extra_plan_field | 1 | COMPLETED | NO_MATCH | synthetic service |
| context_mismatch | 1 | COMPLETED | ValidationError | synthetic service |
| top_k _zero | 0 | ValidationError | Không tạo | synthetic service |
| top_k _bool | 0 | ValidationError | Không tạo | synthetic service |
| top_k _string | 0 | ValidationError | Không tạo | synthetic service |
| missing_mode | 0 | ValidationError | Không tạo | synthetic service |
| rerank_mode | 0 | ValidationError | Không tạo | synthetic service |
| invalid_date | 0 | ValidationError | Không tạo | synthetic service |
| missing_date | 0 | ValidationError | Không tạo | synthetic service |
| empty_policy | 0 | ValidationError | Không tạo | synthetic service |
| blank_policy | 0 | ValidationError | Không tạo | synthetic service |
| number_policy | 0 | ValidationError | Không tạo | synthetic service |
| extra_option | 0 | ValidationError | Không tạo | synthetic service |
| normalized_options | 1 | COMPLETED | NO_MATCH | synthetic service |
| clarification_invalid_options | 0 | ValidationError | Không tạo | synthetic service |

## 9 graph invocations: packet do node tạo

| Case | Graph final status | Lifecycle | Calls | Handoff | Response types |
|---|---|---|---|---|---|
| graph_bm25 | SEARCH_COMPLETED | succeeded | 1 | READY | RetrievalResponse |
| graph_dense | SEARCH_COMPLETED | succeeded | 1 | READY | RetrievalResponse |
| graph_hybrid | SEARCH_COMPLETED | succeeded | 1 | READY | HybridRetrievalResponse |
| graph_rerank | SEARCH_COMPLETED | succeeded | 1 | READY | RerankedHybridRetrievalResponse |
| graph_no_match | NO_MATCH | succeeded | 1 | NO_MATCH | RetrievalResponse |
| graph_clarification | CLARIFICATION_REQUIRED | succeeded | 0 | Không có | |
| graph_failure | RETRIEVAL_FAILED | succeeded | 2 | RETRIEVAL_FAILED | RetrievalResponse, RetrievalResponse |
| graph_exception | RuntimeError | failed | 2 | Không có | |
| graph_context_mismatch | ValidationError | failed | 1 | Không có | |

Các graph input có cùng options theo profile nhưng fresh ExecutionContext IDs. Full state/handoff/requests/responses nằm graph_traces trong JSON; đây là actual compiled LangGraph dùng real service/fake ports hoặc synthetic Recorder. No final state khi exception không được thay bằng packet giả.

### Standalone vs graph: actual observed parity

- bm25:response equality bỏ request_id /retrieved_at = ** True **; Search COMPLETED, graph SEARCH_COMPLETED, packet READY. Hai invocations độc lập không cùng UUID /timestamp.
- dense:response equality bỏ request_id /retrieved_at = ** True **; Search COMPLETED, graph SEARCH_COMPLETED, packet READY. Hai invocations độc lập không cùng UUID /timestamp.
- hybrid:response equality bỏ request_id /retrieved_at = ** True **; Search COMPLETED, graph SEARCH_COMPLETED, packet READY. Hai invocations độc lập không cùng UUID /timestamp.
- rerank:response equality bỏ request_id /retrieved_at = ** True **; Search COMPLETED, graph SEARCH_COMPLETED, packet READY. Hai invocations độc lập không cùng UUID /timestamp.

Standalone không trả handoff; graph giữ SearchState và thêm packet/context/status map. Clarification direct có SearchState empty; graph skip cả Search node và search_result/handoff là None. Graph failure classified lifecycle succeeded khác execution exception lifecycle failed.

## Supplemental probes

[supplemental-probes.json](evidence/supplemental-probes.json):missing raw node state.plan → KeyError. Synthetic packet copy với source_metadata chứa object() → PydanticSerializationError khi model_dump_json; không thay đổi stored metadata. Runtime type object là allowed value cho dict[str, object] nhưng không mọi object JSON -serializable.

## Historical live evidence tách riêng

Các executions Supabase Task 4/5 được tổng hợp ở 14 và [historical-live-summary.json](evidence/historical-live-summary.json). Chúng không thuộc 35+9 invocations mới và không được gắn nhãn đã chạy lại Task 6B.
