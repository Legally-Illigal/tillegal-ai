# Query node

Owner QuerySearchNodes.query trong src/applications/tillegal/graphs/legal_qa.py; line ranges ở03. Input state.question từ wrapper; IDs của run không đổi.

Node gọi understand đúng một lần. Validation/NFC/date/prefix/split/topic rules tiếp tục thuộc agents/query/agent.py. Output plan dict, trusted options, clarification và status; reset handoff/search_result None. Node không có Supabase/retrieval call.

Nếu clarification truthy, status CLARIFICATION_REQUIRED, route end và graph END. Nếu không, intermediate QUERY_COMPLETED rồi Search. Câu Có được không? và31/02/2024 có zero retrieval calls và stream chỉ query node trong tests. Điều kiện này dựa trên Query result, chưa đánh giá legal sufficiency.

Original giữ đối số kể cả whitespace/NFD; subquery dùng NFC nội bộ. Graph Unicode test xác minh original đến tận JSON handoff, không đổi input thành lower/normalized original.

Invalid type/blank/control giữ QueryInputError(ValueError) hiện hữu; GraphExecutor lifecycle FAILED và propagate. Unexpected RuntimeError Query cũng propagate, không biến thành clarification/no-match. Không thêm public API error wrapper. Lifecycle.error là diagnostic nội bộ, không xuất verbatim ra client tương lai.

Tests có direct node/routing, clarification graph stream, invalid input, forced Query failure, Unicode và dependency isolation. Không phát triển taxonomy, Query LLM, expansion hoặc retry mới. Overall deadline theo executor; hàm deterministic nhỏ có length limit, chưa có hard native interruption theo từng regex step.
