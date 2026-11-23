# Runtime traces: standalone Query và graph giả lập

52 synthetic cases;không real DB/model/LLM. Full data tại [query-traces-complete.json](evidence/query-traces-complete.json),capture sys.settrace chỉ trên code object understand. 42 cases đầu giữ tại query-traces.json;10 cases bổ sung không làm52 thành94.

## Nhãn chứng cứ

- OBSERVED: input,locals capture,final output/exception của code thật.
- OBSERVED_WITH_FAKE_RETRIEVAL: graph thật với FakeRetrieval;NO_MATCH chỉ là fixture outcome,không đánh giá DB.
- SOURCE-DERIVED: rule explanation hoặc pattern re-evaluation từ source,không phải local variable được code lưu.
- ILLUSTRATIVE: ví dụ sư phạm ngoài danh sách;không gán nhãn execution.

Field diagnostic post_validation được capture ngay trước dòng37:chỉ type/length/control prechecks đã qua;blank check38 còn phía sau. Nó không khẳng định toàn validation thành công. Final plan tồn tại mới cho thấy entrypoint trả bình thường. Post_normalization ở event trước38 là local text thật.

## Case `ordinary`

**OBSERVED input**

```json
"Người lao động được nghỉ phép bao nhiêu ngày?"
```

**OBSERVED intermediate values**

```json
{
  "raw_prechecks_passed_value": "Người lao động được nghỉ phép bao nhiêu ngày?",
  "normalized_text": "Người lao động được nghỉ phép bao nhiêu ngày?",
  "parts": [
    "Người lao động được nghỉ phép bao nhiêu ngày"
  ],
  "prefix_match": null,
  "topic": "",
  "quote_only": false,
  "raw_temporal_matches": [],
  "dates": [],
  "invalid_date": false,
  "queries_before_topics": [
    "Người lao động được nghỉ phép bao nhiêu ngày"
  ],
  "raw_topic_matches": [
    {
      "group": "nghỉ phép",
      "span": [
        20,
        29
      ]
    }
  ]
}
```

SOURCE-DERIVED domain keyword matches (re-evaluate cùng rule91,không local của understand): `["lao động", "nghỉ phép"]`. Intent rule outcome quote_only ở trên là observed;meaning của rule lấy từ45–48/90.

**OBSERVED final QueryPlan**

```json
{
  "original": "Người lao động được nghỉ phép bao nhiêu ngày?",
  "intent": "legal_question",
  "domain": "labour",
  "temporal_scope": [],
  "subqueries": [
    {
      "text": "Người lao động được nghỉ phép bao nhiêu ngày",
      "purpose": "question_part"
    },
    {
      "text": "nghỉ phép",
      "purpose": "topic"
    }
  ],
  "clarification": null
}
```

**OBSERVED graph với fake retrieval**

```json
{
  "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
  "status": "NO_MATCH",
  "retrieval_calls": 2,
  "handoff_status": "NO_MATCH"
}
```

## Case `lookup`

**OBSERVED input**

```json
"Trích dẫn: đối thoại"
```

**OBSERVED intermediate values**

```json
{
  "raw_prechecks_passed_value": "Trích dẫn: đối thoại",
  "normalized_text": "Trích dẫn: đối thoại",
  "parts": [
    "Trích dẫn: đối thoại"
  ],
  "prefix_match": {
    "group": "Trích dẫn: ",
    "span": [
      0,
      11
    ]
  },
  "topic": "đối thoại",
  "quote_only": true,
  "raw_temporal_matches": [],
  "dates": [],
  "invalid_date": false,
  "queries_before_topics": [
    "đối thoại"
  ],
  "raw_topic_matches": []
}
```

SOURCE-DERIVED domain keyword matches (re-evaluate cùng rule91,không local của understand): `[]`. Intent rule outcome quote_only ở trên là observed;meaning của rule lấy từ45–48/90.

**OBSERVED final QueryPlan**

```json
{
  "original": "Trích dẫn: đối thoại",
  "intent": "quote_lookup",
  "domain": "unknown",
  "temporal_scope": [],
  "subqueries": [
    {
      "text": "đối thoại",
      "purpose": "lookup"
    }
  ],
  "clarification": null
}
```

**OBSERVED graph với fake retrieval**

```json
{
  "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
  "status": "NO_MATCH",
  "retrieval_calls": 1,
  "handoff_status": "NO_MATCH"
}
```

## Case `ambiguous`

**OBSERVED input**

```json
"Có được không?"
```

**OBSERVED intermediate values**

```json
{
  "raw_prechecks_passed_value": "Có được không?",
  "normalized_text": "Có được không?",
  "parts": [
    "Có được không"
  ],
  "prefix_match": null,
  "topic": "",
  "quote_only": false,
  "raw_temporal_matches": [],
  "dates": [],
  "invalid_date": false,
  "queries_before_topics": [
    "Có được không"
  ],
  "raw_topic_matches": []
}
```

SOURCE-DERIVED domain keyword matches (re-evaluate cùng rule91,không local của understand): `[]`. Intent rule outcome quote_only ở trên là observed;meaning của rule lấy từ45–48/90.

**OBSERVED final QueryPlan**

```json
{
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
}
```

**OBSERVED graph với fake retrieval**

```json
{
  "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
  "status": "CLARIFICATION_REQUIRED",
  "retrieval_calls": 0,
  "handoff_status": null
}
```

## Case `invalid_date`

**OBSERVED input**

```json
"Quy định ngày 31/02/2024"
```

**OBSERVED intermediate values**

```json
{
  "raw_prechecks_passed_value": "Quy định ngày 31/02/2024",
  "normalized_text": "Quy định ngày 31/02/2024",
  "parts": [
    "Quy định ngày 31/02/2024"
  ],
  "prefix_match": null,
  "topic": "",
  "quote_only": false,
  "raw_temporal_matches": [
    {
      "group": "31/02/2024",
      "span": [
        14,
        24
      ]
    }
  ],
  "dates": [],
  "invalid_date": true,
  "queries_before_topics": [
    "Quy định ngày 31/02/2024"
  ],
  "raw_topic_matches": []
}
```

SOURCE-DERIVED domain keyword matches (re-evaluate cùng rule91,không local của understand): `[]`. Intent rule outcome quote_only ở trên là observed;meaning của rule lấy từ45–48/90.

**OBSERVED final QueryPlan**

```json
{
  "original": "Quy định ngày 31/02/2024",
  "intent": "legal_question",
  "domain": "unknown",
  "temporal_scope": [],
  "subqueries": [
    {
      "text": "Quy định ngày 31/02/2024",
      "purpose": "question_part"
    }
  ],
  "clarification": "Ngày được nêu không hợp lệ. Bạn vui lòng kiểm tra lại ngày, tháng và năm."
}
```

**OBSERVED graph với fake retrieval**

```json
{
  "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
  "status": "CLARIFICATION_REQUIRED",
  "retrieval_calls": 0,
  "handoff_status": null
}
```

## Case `leap_date`

**OBSERVED input**

```json
"Quy định ngày 29/02/2024"
```

**OBSERVED intermediate values**

```json
{
  "raw_prechecks_passed_value": "Quy định ngày 29/02/2024",
  "normalized_text": "Quy định ngày 29/02/2024",
  "parts": [
    "Quy định ngày 29/02/2024"
  ],
  "prefix_match": null,
  "topic": "",
  "quote_only": false,
  "raw_temporal_matches": [
    {
      "group": "29/02/2024",
      "span": [
        14,
        24
      ]
    }
  ],
  "dates": [
    "29/02/2024"
  ],
  "invalid_date": false,
  "queries_before_topics": [
    "Quy định ngày 29/02/2024"
  ],
  "raw_topic_matches": []
}
```

SOURCE-DERIVED domain keyword matches (re-evaluate cùng rule91,không local của understand): `[]`. Intent rule outcome quote_only ở trên là observed;meaning của rule lấy từ45–48/90.

**OBSERVED final QueryPlan**

```json
{
  "original": "Quy định ngày 29/02/2024",
  "intent": "legal_question",
  "domain": "unknown",
  "temporal_scope": [
    "29/02/2024"
  ],
  "subqueries": [
    {
      "text": "Quy định ngày 29/02/2024",
      "purpose": "question_part"
    }
  ],
  "clarification": null
}
```

**OBSERVED graph với fake retrieval**

```json
{
  "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
  "status": "NO_MATCH",
  "retrieval_calls": 1,
  "handoff_status": "NO_MATCH"
}
```

## Case `year`

**OBSERVED input**

```json
"Quy định năm 2024"
```

**OBSERVED intermediate values**

```json
{
  "raw_prechecks_passed_value": "Quy định năm 2024",
  "normalized_text": "Quy định năm 2024",
  "parts": [
    "Quy định năm 2024"
  ],
  "prefix_match": null,
  "topic": "",
  "quote_only": false,
  "raw_temporal_matches": [
    {
      "group": "2024",
      "span": [
        13,
        17
      ]
    }
  ],
  "dates": [
    "2024"
  ],
  "invalid_date": false,
  "queries_before_topics": [
    "Quy định năm 2024"
  ],
  "raw_topic_matches": []
}
```

SOURCE-DERIVED domain keyword matches (re-evaluate cùng rule91,không local của understand): `[]`. Intent rule outcome quote_only ở trên là observed;meaning của rule lấy từ45–48/90.

**OBSERVED final QueryPlan**

```json
{
  "original": "Quy định năm 2024",
  "intent": "legal_question",
  "domain": "unknown",
  "temporal_scope": [
    "2024"
  ],
  "subqueries": [
    {
      "text": "Quy định năm 2024",
      "purpose": "question_part"
    }
  ],
  "clarification": null
}
```

**OBSERVED graph với fake retrieval**

```json
{
  "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
  "status": "NO_MATCH",
  "retrieval_calls": 1,
  "handoff_status": "NO_MATCH"
}
```

## Case `nfc`

**OBSERVED input**

```json
"  Người lao động được nghỉ phép bao nhiêu ngày?  "
```

Unicode codepoint representation,OBSERVED diagnostic transformation: `  Ng\u01b0\u1eddi lao \u0111\u1ed9ng \u0111\u01b0\u1ee3c ngh\u1ec9 ph\xe9p bao nhi\xeau ng\xe0y?  `.

**OBSERVED intermediate values**

```json
{
  "raw_prechecks_passed_value": "  Người lao động được nghỉ phép bao nhiêu ngày?  ",
  "normalized_text": "Người lao động được nghỉ phép bao nhiêu ngày?",
  "parts": [
    "Người lao động được nghỉ phép bao nhiêu ngày"
  ],
  "prefix_match": null,
  "topic": "",
  "quote_only": false,
  "raw_temporal_matches": [],
  "dates": [],
  "invalid_date": false,
  "queries_before_topics": [
    "Người lao động được nghỉ phép bao nhiêu ngày"
  ],
  "raw_topic_matches": [
    {
      "group": "nghỉ phép",
      "span": [
        20,
        29
      ]
    }
  ]
}
```

SOURCE-DERIVED domain keyword matches (re-evaluate cùng rule91,không local của understand): `["lao động", "nghỉ phép"]`. Intent rule outcome quote_only ở trên là observed;meaning của rule lấy từ45–48/90.

**OBSERVED final QueryPlan**

```json
{
  "original": "  Người lao động được nghỉ phép bao nhiêu ngày?  ",
  "intent": "legal_question",
  "domain": "labour",
  "temporal_scope": [],
  "subqueries": [
    {
      "text": "Người lao động được nghỉ phép bao nhiêu ngày",
      "purpose": "question_part"
    },
    {
      "text": "nghỉ phép",
      "purpose": "topic"
    }
  ],
  "clarification": null
}
```

**OBSERVED graph với fake retrieval**

```json
{
  "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
  "status": "NO_MATCH",
  "retrieval_calls": 2,
  "handoff_status": "NO_MATCH"
}
```

## Case `nfd`

**OBSERVED input**

```json
"  Người lao động được nghỉ phép bao nhiêu ngày?  "
```

Unicode codepoint representation,OBSERVED diagnostic transformation: `  Ngu\u031bo\u031b\u0300i lao \u0111o\u0323\u0302ng \u0111u\u031bo\u031b\u0323c nghi\u0309 phe\u0301p bao nhie\u0302u nga\u0300y?  `.

**OBSERVED intermediate values**

```json
{
  "raw_prechecks_passed_value": "  Người lao động được nghỉ phép bao nhiêu ngày?  ",
  "normalized_text": "Người lao động được nghỉ phép bao nhiêu ngày?",
  "parts": [
    "Người lao động được nghỉ phép bao nhiêu ngày"
  ],
  "prefix_match": null,
  "topic": "",
  "quote_only": false,
  "raw_temporal_matches": [],
  "dates": [],
  "invalid_date": false,
  "queries_before_topics": [
    "Người lao động được nghỉ phép bao nhiêu ngày"
  ],
  "raw_topic_matches": [
    {
      "group": "nghỉ phép",
      "span": [
        20,
        29
      ]
    }
  ]
}
```

SOURCE-DERIVED domain keyword matches (re-evaluate cùng rule91,không local của understand): `["lao động", "nghỉ phép"]`. Intent rule outcome quote_only ở trên là observed;meaning của rule lấy từ45–48/90.

**OBSERVED final QueryPlan**

```json
{
  "original": "  Người lao động được nghỉ phép bao nhiêu ngày?  ",
  "intent": "legal_question",
  "domain": "labour",
  "temporal_scope": [],
  "subqueries": [
    {
      "text": "Người lao động được nghỉ phép bao nhiêu ngày",
      "purpose": "question_part"
    },
    {
      "text": "nghỉ phép",
      "purpose": "topic"
    }
  ],
  "clarification": null
}
```

**OBSERVED graph với fake retrieval**

```json
{
  "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
  "status": "NO_MATCH",
  "retrieval_calls": 2,
  "handoff_status": "NO_MATCH"
}
```

## Case `multiple`

**OBSERVED input**

```json
"Đối thoại định kỳ? Nghỉ phép; Tiền lương"
```

**OBSERVED intermediate values**

```json
{
  "raw_prechecks_passed_value": "Đối thoại định kỳ? Nghỉ phép; Tiền lương",
  "normalized_text": "Đối thoại định kỳ? Nghỉ phép; Tiền lương",
  "parts": [
    "Đối thoại định kỳ",
    "Nghỉ phép",
    "Tiền lương"
  ],
  "prefix_match": null,
  "topic": "",
  "quote_only": false,
  "raw_temporal_matches": [],
  "dates": [],
  "invalid_date": false,
  "queries_before_topics": [
    "Đối thoại định kỳ",
    "Nghỉ phép",
    "Tiền lương"
  ],
  "raw_topic_matches": [
    {
      "group": "Đối thoại định kỳ",
      "span": [
        0,
        17
      ]
    },
    {
      "group": "Nghỉ phép",
      "span": [
        19,
        28
      ]
    },
    {
      "group": "Tiền lương",
      "span": [
        30,
        40
      ]
    }
  ]
}
```

SOURCE-DERIVED domain keyword matches (re-evaluate cùng rule91,không local của understand): `["Nghỉ phép", "Tiền lương"]`. Intent rule outcome quote_only ở trên là observed;meaning của rule lấy từ45–48/90.

**OBSERVED final QueryPlan**

```json
{
  "original": "Đối thoại định kỳ? Nghỉ phép; Tiền lương",
  "intent": "legal_question",
  "domain": "labour",
  "temporal_scope": [],
  "subqueries": [
    {
      "text": "Đối thoại định kỳ",
      "purpose": "question_part"
    },
    {
      "text": "Nghỉ phép",
      "purpose": "question_part"
    },
    {
      "text": "Tiền lương",
      "purpose": "question_part"
    }
  ],
  "clarification": null
}
```

**OBSERVED graph với fake retrieval**

```json
{
  "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
  "status": "NO_MATCH",
  "retrieval_calls": 3,
  "handoff_status": "NO_MATCH"
}
```

## Case `multi_rule`

**OBSERVED input**

```json
"Trích dẫn: tiền lương ngày 31/02/2024"
```

**OBSERVED intermediate values**

```json
{
  "raw_prechecks_passed_value": "Trích dẫn: tiền lương ngày 31/02/2024",
  "normalized_text": "Trích dẫn: tiền lương ngày 31/02/2024",
  "parts": [
    "Trích dẫn: tiền lương ngày 31/02/2024"
  ],
  "prefix_match": {
    "group": "Trích dẫn: ",
    "span": [
      0,
      11
    ]
  },
  "topic": "tiền lương ngày 31/02/2024",
  "quote_only": true,
  "raw_temporal_matches": [
    {
      "group": "31/02/2024",
      "span": [
        27,
        37
      ]
    }
  ],
  "dates": [],
  "invalid_date": true,
  "queries_before_topics": [
    "tiền lương ngày 31/02/2024"
  ],
  "raw_topic_matches": []
}
```

SOURCE-DERIVED domain keyword matches (re-evaluate cùng rule91,không local của understand): `["tiền lương"]`. Intent rule outcome quote_only ở trên là observed;meaning của rule lấy từ45–48/90.

**OBSERVED final QueryPlan**

```json
{
  "original": "Trích dẫn: tiền lương ngày 31/02/2024",
  "intent": "quote_lookup",
  "domain": "labour",
  "temporal_scope": [],
  "subqueries": [
    {
      "text": "tiền lương ngày 31/02/2024",
      "purpose": "lookup"
    }
  ],
  "clarification": "Ngày được nêu không hợp lệ. Bạn vui lòng kiểm tra lại ngày, tháng và năm."
}
```

**OBSERVED graph với fake retrieval**

```json
{
  "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
  "status": "CLARIFICATION_REQUIRED",
  "retrieval_calls": 0,
  "handoff_status": null
}
```

## Case `too_many`

**OBSERVED input**

```json
"thuế; nghỉ phép; tiền lương; làm thêm giờ; hợp đồng"
```

**OBSERVED intermediate values**

```json
{
  "raw_prechecks_passed_value": "thuế; nghỉ phép; tiền lương; làm thêm giờ; hợp đồng",
  "normalized_text": "thuế; nghỉ phép; tiền lương; làm thêm giờ; hợp đồng",
  "parts": [
    "thuế",
    "nghỉ phép",
    "tiền lương",
    "làm thêm giờ",
    "hợp đồng"
  ],
  "prefix_match": null,
  "topic": "",
  "quote_only": false,
  "raw_temporal_matches": [],
  "dates": [],
  "invalid_date": false,
  "queries_before_topics": [
    "thuế",
    "nghỉ phép",
    "tiền lương",
    "làm thêm giờ"
  ],
  "raw_topic_matches": [
    {
      "group": "nghỉ phép",
      "span": [
        6,
        15
      ]
    },
    {
      "group": "tiền lương",
      "span": [
        17,
        27
      ]
    },
    {
      "group": "làm thêm giờ",
      "span": [
        29,
        41
      ]
    }
  ]
}
```

SOURCE-DERIVED domain keyword matches (re-evaluate cùng rule91,không local của understand): `["nghỉ phép", "tiền lương"]`. Intent rule outcome quote_only ở trên là observed;meaning của rule lấy từ45–48/90.

**OBSERVED final QueryPlan**

```json
{
  "original": "thuế; nghỉ phép; tiền lương; làm thêm giờ; hợp đồng",
  "intent": "legal_question",
  "domain": "labour",
  "temporal_scope": [],
  "subqueries": [
    {
      "text": "thuế",
      "purpose": "question_part"
    },
    {
      "text": "nghỉ phép",
      "purpose": "question_part"
    },
    {
      "text": "tiền lương",
      "purpose": "question_part"
    },
    {
      "text": "làm thêm giờ",
      "purpose": "question_part"
    }
  ],
  "clarification": "Vui lòng chia câu hỏi thành tối đa bốn phần."
}
```

**OBSERVED graph với fake retrieval**

```json
{
  "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
  "status": "CLARIFICATION_REQUIRED",
  "retrieval_calls": 0,
  "handoff_status": null
}
```

## Case `override`

**OBSERVED input**

```json
"thuế; nghỉ phép; tiền lương; điều kiện; 31/02/2024"
```

**OBSERVED intermediate values**

```json
{
  "raw_prechecks_passed_value": "thuế; nghỉ phép; tiền lương; điều kiện; 31/02/2024",
  "normalized_text": "thuế; nghỉ phép; tiền lương; điều kiện; 31/02/2024",
  "parts": [
    "thuế",
    "nghỉ phép",
    "tiền lương",
    "điều kiện",
    "31/02/2024"
  ],
  "prefix_match": null,
  "topic": "",
  "quote_only": false,
  "raw_temporal_matches": [
    {
      "group": "31/02/2024",
      "span": [
        40,
        50
      ]
    }
  ],
  "dates": [],
  "invalid_date": true,
  "queries_before_topics": [
    "thuế",
    "nghỉ phép",
    "tiền lương",
    "điều kiện"
  ],
  "raw_topic_matches": [
    {
      "group": "nghỉ phép",
      "span": [
        6,
        15
      ]
    },
    {
      "group": "tiền lương",
      "span": [
        17,
        27
      ]
    }
  ]
}
```

SOURCE-DERIVED domain keyword matches (re-evaluate cùng rule91,không local của understand): `["nghỉ phép", "tiền lương"]`. Intent rule outcome quote_only ở trên là observed;meaning của rule lấy từ45–48/90.

**OBSERVED final QueryPlan**

```json
{
  "original": "thuế; nghỉ phép; tiền lương; điều kiện; 31/02/2024",
  "intent": "legal_question",
  "domain": "labour",
  "temporal_scope": [],
  "subqueries": [
    {
      "text": "thuế",
      "purpose": "question_part"
    },
    {
      "text": "nghỉ phép",
      "purpose": "question_part"
    },
    {
      "text": "tiền lương",
      "purpose": "question_part"
    },
    {
      "text": "điều kiện",
      "purpose": "question_part"
    }
  ],
  "clarification": "Ngày được nêu không hợp lệ. Bạn vui lòng kiểm tra lại ngày, tháng và năm."
}
```

**OBSERVED graph với fake retrieval**

```json
{
  "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
  "status": "CLARIFICATION_REQUIRED",
  "retrieval_calls": 0,
  "handoff_status": null
}
```

## Case `prefix_empty`

**OBSERVED input**

```json
"Trích dẫn:"
```

**OBSERVED intermediate values**

```json
{
  "raw_prechecks_passed_value": "Trích dẫn:",
  "normalized_text": "Trích dẫn:",
  "parts": [
    "Trích dẫn:"
  ],
  "prefix_match": {
    "group": "Trích dẫn:",
    "span": [
      0,
      10
    ]
  },
  "topic": "",
  "quote_only": false,
  "raw_temporal_matches": [],
  "dates": [],
  "invalid_date": false,
  "queries_before_topics": [
    "Trích dẫn:"
  ],
  "raw_topic_matches": []
}
```

SOURCE-DERIVED domain keyword matches (re-evaluate cùng rule91,không local của understand): `[]`. Intent rule outcome quote_only ở trên là observed;meaning của rule lấy từ45–48/90.

**OBSERVED final QueryPlan**

```json
{
  "original": "Trích dẫn:",
  "intent": "legal_question",
  "domain": "unknown",
  "temporal_scope": [],
  "subqueries": [
    {
      "text": "Trích dẫn:",
      "purpose": "question_part"
    }
  ],
  "clarification": "Bạn cần tra cứu quy định hoặc tình huống cụ thể nào?"
}
```

**OBSERVED graph với fake retrieval**

```json
{
  "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
  "status": "CLARIFICATION_REQUIRED",
  "retrieval_calls": 0,
  "handoff_status": null
}
```

## Case `base_duplicates`

**OBSERVED input**

```json
"nghỉ phép; nghỉ phép"
```

**OBSERVED intermediate values**

```json
{
  "raw_prechecks_passed_value": "nghỉ phép; nghỉ phép",
  "normalized_text": "nghỉ phép; nghỉ phép",
  "parts": [
    "nghỉ phép",
    "nghỉ phép"
  ],
  "prefix_match": null,
  "topic": "",
  "quote_only": false,
  "raw_temporal_matches": [],
  "dates": [],
  "invalid_date": false,
  "queries_before_topics": [
    "nghỉ phép",
    "nghỉ phép"
  ],
  "raw_topic_matches": [
    {
      "group": "nghỉ phép",
      "span": [
        0,
        9
      ]
    },
    {
      "group": "nghỉ phép",
      "span": [
        11,
        20
      ]
    }
  ]
}
```

SOURCE-DERIVED domain keyword matches (re-evaluate cùng rule91,không local của understand): `["nghỉ phép", "nghỉ phép"]`. Intent rule outcome quote_only ở trên là observed;meaning của rule lấy từ45–48/90.

**OBSERVED final QueryPlan**

```json
{
  "original": "nghỉ phép; nghỉ phép",
  "intent": "legal_question",
  "domain": "labour",
  "temporal_scope": [],
  "subqueries": [
    {
      "text": "nghỉ phép",
      "purpose": "question_part"
    },
    {
      "text": "nghỉ phép",
      "purpose": "question_part"
    }
  ],
  "clarification": null
}
```

**OBSERVED graph với fake retrieval**

```json
{
  "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
  "status": "NO_MATCH",
  "retrieval_calls": 2,
  "handoff_status": "NO_MATCH"
}
```

## Case `iso_date`

**OBSERVED input**

```json
"Quy định ngày 2024-02-29"
```

**OBSERVED intermediate values**

```json
{
  "raw_prechecks_passed_value": "Quy định ngày 2024-02-29",
  "normalized_text": "Quy định ngày 2024-02-29",
  "parts": [
    "Quy định ngày 2024-02-29"
  ],
  "prefix_match": null,
  "topic": "",
  "quote_only": false,
  "raw_temporal_matches": [
    {
      "group": "2024",
      "span": [
        14,
        18
      ]
    }
  ],
  "dates": [
    "2024"
  ],
  "invalid_date": false,
  "queries_before_topics": [
    "Quy định ngày 2024-02-29"
  ],
  "raw_topic_matches": []
}
```

SOURCE-DERIVED domain keyword matches (re-evaluate cùng rule91,không local của understand): `[]`. Intent rule outcome quote_only ở trên là observed;meaning của rule lấy từ45–48/90.

**OBSERVED final QueryPlan**

```json
{
  "original": "Quy định ngày 2024-02-29",
  "intent": "legal_question",
  "domain": "unknown",
  "temporal_scope": [
    "2024"
  ],
  "subqueries": [
    {
      "text": "Quy định ngày 2024-02-29",
      "purpose": "question_part"
    }
  ],
  "clarification": null
}
```

**OBSERVED graph với fake retrieval**

```json
{
  "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
  "status": "NO_MATCH",
  "retrieval_calls": 1,
  "handoff_status": "NO_MATCH"
}
```

## Case `tab_part`

**OBSERVED input**

```json
"Quy định thuế; \t ;nghỉ phép"
```

**OBSERVED intermediate values**

```json
{
  "raw_prechecks_passed_value": "Quy định thuế; \t ;nghỉ phép",
  "normalized_text": "Quy định thuế; \t ;nghỉ phép",
  "parts": [
    "Quy định thuế",
    "\t",
    "nghỉ phép"
  ],
  "prefix_match": null,
  "topic": "",
  "quote_only": false,
  "raw_temporal_matches": [],
  "dates": [],
  "invalid_date": false,
  "queries_before_topics": [
    "Quy định thuế",
    "\t",
    "nghỉ phép"
  ],
  "raw_topic_matches": [
    {
      "group": "nghỉ phép",
      "span": [
        18,
        27
      ]
    }
  ]
}
```

SOURCE-DERIVED domain keyword matches (re-evaluate cùng rule91,không local của understand): `["nghỉ phép"]`. Intent rule outcome quote_only ở trên là observed;meaning của rule lấy từ45–48/90.

**OBSERVED final QueryPlan**

```json
{
  "original": "Quy định thuế; \t ;nghỉ phép",
  "intent": "legal_question",
  "domain": "labour",
  "temporal_scope": [],
  "subqueries": [
    {
      "text": "Quy định thuế",
      "purpose": "question_part"
    },
    {
      "text": "\t",
      "purpose": "question_part"
    },
    {
      "text": "nghỉ phép",
      "purpose": "question_part"
    }
  ],
  "clarification": null
}
```

**OBSERVED graph với fake retrieval**

```json
{
  "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
  "exception_type": "ValidationError",
  "error_code": null,
  "retrieval_calls": 0
}
```

## Case `punctuation`

**OBSERVED input**

```json
"? ;"
```

**OBSERVED intermediate values**

```json
{
  "raw_prechecks_passed_value": "? ;",
  "normalized_text": "? ;",
  "parts": [],
  "prefix_match": null,
  "topic": "",
  "quote_only": false,
  "raw_temporal_matches": [],
  "dates": [],
  "invalid_date": false,
  "queries_before_topics": [
    "? ;"
  ],
  "raw_topic_matches": []
}
```

SOURCE-DERIVED domain keyword matches (re-evaluate cùng rule91,không local của understand): `[]`. Intent rule outcome quote_only ở trên là observed;meaning của rule lấy từ45–48/90.

**OBSERVED final QueryPlan**

```json
{
  "original": "? ;",
  "intent": "legal_question",
  "domain": "unknown",
  "temporal_scope": [],
  "subqueries": [
    {
      "text": "? ;",
      "purpose": "question_part"
    }
  ],
  "clarification": null
}
```

**OBSERVED graph với fake retrieval**

```json
{
  "label": "OBSERVED_WITH_FAKE_RETRIEVAL",
  "status": "NO_MATCH",
  "retrieval_calls": 1,
  "handoff_status": "NO_MATCH"
}
```

## Tổng hợp52 cases và outcome

| Case ID | Intent | Domain | Số subqueries | Clarification? | Graph status/exception | Retrieval calls giả |
|---|---|---|---|---|---|---|
| ordinary | legal_question | labour | 2 | False | NO_MATCH | 2 |
| lookup | quote_lookup | unknown | 1 | False | NO_MATCH | 1 |
| ambiguous | legal_question | unknown | 1 | True | CLARIFICATION_REQUIRED | 0 |
| invalid_date | legal_question | unknown | 1 | True | CLARIFICATION_REQUIRED | 0 |
| leap_date | legal_question | unknown | 1 | False | NO_MATCH | 1 |
| year | legal_question | unknown | 1 | False | NO_MATCH | 1 |
| nfc | legal_question | labour | 2 | False | NO_MATCH | 2 |
| nfd | legal_question | labour | 2 | False | NO_MATCH | 2 |
| multiple | legal_question | labour | 3 | False | NO_MATCH | 3 |
| multi_rule | quote_lookup | labour | 1 | True | CLARIFICATION_REQUIRED | 0 |
| too_many | legal_question | labour | 4 | True | CLARIFICATION_REQUIRED | 0 |
| override | legal_question | labour | 4 | True | CLARIFICATION_REQUIRED | 0 |
| prefix_empty | legal_question | unknown | 1 | True | CLARIFICATION_REQUIRED | 0 |
| single_word | legal_question | unknown | 1 | True | CLARIFICATION_REQUIRED | 0 |
| bare_prefix | legal_question | unknown | 1 | False | NO_MATCH | 1 |
| relative | legal_question | unknown | 1 | False | NO_MATCH | 1 |
| unsupported_relative | legal_question | unknown | 1 | False | NO_MATCH | 1 |
| partial_month | legal_question | unknown | 1 | False | NO_MATCH | 1 |
| partial_day | legal_question | unknown | 1 | False | NO_MATCH | 1 |
| iso_date | legal_question | unknown | 1 | False | NO_MATCH | 1 |
| repeated_year | legal_question | unknown | 1 | False | NO_MATCH | 1 |
| base_duplicates | legal_question | labour | 2 | False | NO_MATCH | 2 |
| guarded_and | legal_question | labour | 3 | False | NO_MATCH | 3 |
| plain_and | legal_question | labour | 3 | False | NO_MATCH | 3 |
| topic_cap | legal_question | labour | 4 | False | NO_MATCH | 4 |
| punctuation | legal_question | unknown | 1 | False | NO_MATCH | 1 |
| tab_part | legal_question | labour | 3 | False | ValidationError | 0 |
| negated_domain | legal_question | labour | 1 | False | NO_MATCH | 1 |
| domain_miss | legal_question | unknown | 1 | False | NO_MATCH | 1 |
| law_number | legal_question | unknown | 1 | False | NO_MATCH | 1 |
| lookup_multi | legal_question | labour | 2 | False | NO_MATCH | 2 |
| extra_space_prefix | legal_question | unknown | 1 | False | NO_MATCH | 1 |
| quoted_lookup | quote_lookup | unknown | 1 | False | NO_MATCH | 1 |
| old_leap_invalid | legal_question | unknown | 1 | True | CLARIFICATION_REQUIRED | 0 |
| relative_current | legal_question | unknown | 1 | False | NO_MATCH | 1 |
| zero_width | legal_question | unknown | 1 | True | CLARIFICATION_REQUIRED | 0 |
| empty | Không plan | N/A | N/A | N/A | QueryInputError | 0 |
| whitespace | Không plan | N/A | N/A | N/A | QueryInputError | 0 |
| non_string | Không plan | N/A | N/A | N/A | QueryInputError | 0 |
| length | Không plan | N/A | N/A | N/A | QueryInputError | 0 |
| control | Không plan | N/A | N/A | N/A | QueryInputError | 0 |
| surrogate | Không plan | N/A | N/A | N/A | QueryInputError | 0 |
| annual_leave | legal_question | unknown | 2 | False | NO_MATCH | 2 |
| termination | legal_question | labour | 2 | False | NO_MATCH | 2 |
| lookup_find | quote_lookup | labour | 1 | False | NO_MATCH | 1 |
| ambiguous_ref | legal_question | unknown | 1 | True | CLARIFICATION_REQUIRED | 0 |
| ambiguous_case | legal_question | unknown | 1 | True | CLARIFICATION_REQUIRED | 0 |
| year_1999 | legal_question | unknown | 1 | False | NO_MATCH | 1 |
| future_year | legal_question | unknown | 1 | False | NO_MATCH | 1 |
| newline_parts | legal_question | labour | 3 | False | NO_MATCH | 3 |
| invalid_and_year | legal_question | unknown | 1 | True | CLARIFICATION_REQUIRED | 0 |
| single_lookup | quote_lookup | unknown | 1 | False | NO_MATCH | 1 |

Ngày sai giữ original/subquery nhưng không scope sai. NFC/NFD giữ original khác,analysis khác chỉ original. Too-many vẫn4 subqueries;clarification không tạo0-subquery plan. Tab-only part là trường hợp plan được trả nhưng request validation fail;punctuation-only có thể đi fake retrieval. Đây là behavior observations,không sửa code hoặc đánh giá semantics đúng luật.
