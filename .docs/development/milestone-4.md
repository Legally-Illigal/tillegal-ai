# Milestone 4 — Evaluation & Context Optimization

Ngày thực hiện: 2026-11-06. Engineering implementation đã có; legal quality validation vẫn pending human review. Không có human-approved gold mới. Không gọi external generation API trong milestone này.

## Architecture và phạm vi thay đổi

`TILLEGAL_CONTEXT_POLICY=legacy|context|context_judge`, mặc định `legacy`. BasicRAG, retrieval, EvidenceBuilder, index và model revisions không đổi. Flag được đọc khi compile graph; thay đổi cấu hình cần tạo lại application/graph.

- A (`legacy`): selection và scheduling hiện có.
- B (`context`): context selection mới, giữ scheduling của Judge cũ. Vì selection thay đổi đầu vào Response, A/B không cô lập riêng chi phí generation.
- C (`context_judge`): cùng context layer, Judge mới phân biệt lexical relevance, answerability UNKNOWN, legal sufficiency NOT_LEGALLY_EVALUATED, conditions/exceptions UNCONFIRMED, giữ temporal/jurisdiction/version guards.

Context layer ở `agents/judge/context_selection.py` chọn nguyên window cùng version/article/scope/form ancestry. Giữ nguyên evidence objects, citation IDs, locators, offsets và hashes. Kiểm tra identity/hash fail closed. Bảo toàn heading, body, conditions và exceptions có trong window; không cắt để vừa budget. Chapeau thiếu hậu duệ phía sau, source incomplete, omissions, quoted scope, placeholder không phù hợp intent hoặc vượt budget dẫn đến abstain. Biểu mẫu được phép khi query có form intent; test cả form không có article nhưng có form boundary hợp lệ.

Đây là heuristic, không chứng minh completeness pháp lý: chọn một window có thể bỏ nguồn ở điều khác. `omitted_candidate_windows` và candidate rejection reasons được lưu trong trace. Numeric/semantic publication guards từ milestone trước giữ nguyên. Judge chỉ refine bằng heading đã xuất hiện trong source, không thêm thuật ngữ pháp lý tùy ý, dừng khi budget/round/no-new-evidence/no-target.

Các nhóm file: `evaluation/annotations.py`, `quality_metrics.py` (contract/metrics); `scripts/evaluate_quality.py`, `export_annotation_draft.py` (runner/export); `scripts/benchmark_context.py`, `summarize_context.py` (A/B/C); `graphs/multi_agent.py`, `legal_qa.py`, `semantic.py` (flag, timing, mock body choice); tests evaluation và pilot markers; `scripts/package_service_handoff.py` (bàn giao); báo cáo/results/handoff. Manifest bàn giao liệt kê đầy đủ before/after hashes.

## Annotation workflow

Đã kiểm lại 12 T5 draft và source locators qua validator; dataset/source_context/REVIEW giữ nguyên checksum manifest. Không câu nào được tự phê duyệt. Source matching chỉ chứng minh quote tồn tại, không chứng minh expected answer/temporal applicability đúng.

`m4-results/t5-contract-draft.json` là bản chuyển schema v2 riêng, SHA256 `7f6bd83d2fbac6853f06e3098f06a89c573a978e0713a7dc27bf6fe2ddb969f5`; original dataset SHA256 `8d5f0d048e5779dc6df9646502e6e5e3725747711bf0699cb3809ab829557e49`. Không đặt relevant_units thành gold từ draft citations.

Reviewer dùng guideline trong annotation-quality.md, bổ sung schema v2:

1. Xác định question ID/domain/intent và thời điểm hỏi. Không suy diễn ngày hiệu lực từ ngày ban hành. UNKNOWN nếu thiếu thông tin chuyển tiếp/sửa đổi.
2. Gắn document/source/version identity và article/clause/point, quote hash, offsets `[start,end)` theo normalized chunk text. Không chuyển offsets giữa các version. Lưu evidence, điều kiện bắt buộc và ngoại lệ thành spans riêng.
3. Đánh dấu relevant units theo đúng đơn vị retrieval đã thống nhất. Null nghĩa là chưa annotate; danh sách rỗng chỉ dùng khi đã review không có relevant unit trong corpus.
4. Viết expected answer hoặc expected abstention, giữ giới hạn số học và đối tượng/phạm vi áp dụng. Đọc đủ body/list và các cross-reference cần thiết; thiếu source không đồng nghĩa claim sai.
5. Annotate claim IDs cố định với SUPPORTED, CONTRADICTED (phải có evidence), INSUFFICIENT_EVIDENCE, hoặc NOT_EVALUATED. Lưu nguồn phản bác cụ thể cho CONTRADICTED. Claim mới từ generation phải được review riêng trước khi tính accuracy.
6. Human-approved/held-out yêu cầu reviewer_type=human, reviewer_id, reviewed_at có timezone. Team chịu trách nhiệm xác thực attestation; schema không xác minh danh tính. Held-out phải được tạo độc lập và không dùng để tuning.

Synthetic fixtures chỉ kiểm toán công thức; exploratory phục vụ chẩn đoán; draft/exploratory không được tính quality score. Review bản sao, không ghi đè dataset gốc.

## Metric contract và validity

Runner nhận Annotation[], Prediction[] cùng Experiment manifest; IDs duy nhất và tập questions phải khớp, kể cả request lỗi. Claim IDs là đơn vị đã annotate, không tự align câu trả lời tự do. Macro-average chỉ trên cases có nhãn hợp lệ; báo `scored_cases`, claim/citation denominators và số unlabelled predictions.

| Metric | Định nghĩa và điều kiện |
|---|---|
| Recall@k | relevant hits trong top k / tổng relevant units; thiếu hoặc zero gold → null |
| Precision@k | relevant hits / k; vị trí thiếu vẫn tính mẫu số k; thiếu gold → null |
| MRR@k | 1/rank relevant đầu tiên trong top k, không hit → 0; thiếu gold → null |
| nDCG@k | tổng binary gain/log2(rank+1) / ideal DCG; zero ideal → null |
| Context coverage | tỷ lệ required spans được phủ toàn bộ bởi hợp các intervals cùng canonical IDs/version/source/hash |
| Condition/exception recall | span coverage riêng theo role; không có nhãn role → null |
| Claim support accuracy | verdict đúng / số claim labels khác NOT_EVALUATED; missing prediction tính sai |
| Citation correctness | tập evidence IDs bằng đúng tập reviewer xác nhận / số gold SUPPORTED claims; không suy ra entailment từ ID |
| Abstention accuracy | expected vs observed abstention, chỉ khi cả hai có nhãn/quyết định |
| Abstention coverage/rate | số observed decisions / attempts; số abstentions / observed decisions; failures tách riêng |
| Latency | nearest-rank p50/p95 trên attempts, gồm failures |
| Tokens/cost | tổng chỉ khi mọi record có usage; USD từ explicit `price_per_million` cho prompt/completion; thiếu → null |

Wilson95 chỉ dành cho abstention accuracy khi >=30 mẫu reviewed độc lập và manifest khai báo independent_samples. Không xuất CI từ 3 lần lặp của 8 exploratory queries. Không có claim về answer relevance/groundedness pháp lý khi chưa review; accuracy trên claim labels không thay thế đánh giá generation toàn diện.

Fixture CLI `metric-*.json` có Recall=.5, Precision=.5, MRR=.5, nDCG=.3868528072, context/condition coverage=1, abstention accuracy=1; exception/claim/citation null vì thiếu labels. Tests tính tay còn kiểm version mismatch, interval gaps, claims contradicted vs insufficient, usage/cost, failures và Wilson. Fixture không phải chất lượng corpus.

## A/B/C exploratory — mock generation

Lưu `before.json` trước sửa source; snapshot `.tmp/m4-before`. 8 queries ×3 repetitions mỗi configuration, cùng BM25 top_k=3, mock model/revision=null, draft workflow. Bốn diagnostic queries cũ và bốn query mới đều đã nhìn thấy khi phát triển, không phải held-out. Không dùng tốc độ mock để dự đoán tốc độ local LLM.

Dataset hash `1a9cdfcb59ebf07e5e0a9778eabd7687be256d7568d2dd3fe5dadb547a0e06bd`; index manifest hash `800a05d08b230c837d0134998ad4800fcf54ff9521f4c53943e77ded514f5eb2`. Từng JSON lưu Python, source hashes, config, trace/IDs; context version context-v1. `summary.json` được tạo bởi summarize_context.py kiểm cùng identities.

| Configuration | E2E p50/p95 ms | Retrieval p50/p95 | Context p50/p95 | Judge p50/p95 | Tool calls | Refines | Abstention |
|---|---:|---:|---:|---:|---:|---:|---:|
| Before (pre-change) | 41.94/69.23 | 30.73/56.83 | 0/0 | chưa instrument | 66 | 24 | 12/24 |
| A legacy | 28.47/44.88 | 21.59/36.91 | 0/0 | .23/.31 | 66 | 24 | 12/24 |
| B context | 30.76/49.86 | 21.98/38.71 | 1.92/3.17 | .25/.45 | 66 | 24 | 12/24 |
| C context_judge | 18.13/61.22 | 10.91/44.99 | 1.03/3.71 | .27/1.16 | 63 | 12 | 15/24 |

Legacy parity trước/sau **true** cho selected IDs, version/hash/chunk metadata, call counts và status. Before khác timing do cache/CPU; không tuyên bố speedup dựa trên cột này. C giảm refines nhưng tăng abstention và p95. Chưa bật flag mới mặc định. Memory không đo, tokens/cost/quality/CI null. Mock Response không mô phỏng schema adherence hoặc token pressure của real generation. Các real Qwen probes ở real-ai-quality.md là evidence milestone trước, không phải A/B/C M4.

## Failure taxonomy và tradeoffs

| Quan sát | Tầng và cách xử lý | Còn hạn chế |
|---|---|---|
| Retrieval có form trống, answer suy diễn số ngày | Context Selection + Response: reject placeholder khi không form intent | Form intent lexical có false positives/negatives; test explicit form được giữ |
| Chọn câu dẫn thiếu điều kiện | Context Selection: yêu cầu hậu duệ phía sau, giữ cả window | Cross-article exceptions chưa thể chứng minh đầy đủ |
| Retrieval có hit nhưng bỏ body | Judge/Selection: group body cùng article; diagnostic từ 0 thành 21 selected rows | 21 rows tăng real model context; chưa đo real generation A/B |
| Query vô nghĩa được refine thêm từ pháp lý | Query/Judge: chỉ refine từ source heading, dừng no-target | Heading lexical có thể không hữu ích; C bảo thủ hơn |
| Một diagnostic insurance B chọn 5 rows, C không chọn | Scheduling/Judge: dừng sớm khác legacy | False-negative risk, giữ opt-in; cần reviewed labels trước đổi default |
| Verifier nhầm khác đối tượng là contradicted | Verification: giữ trạng thái/trace riêng | M4 không sửa model hoặc chứng minh semantic accuracy |
| Claim mất “ít nhất/không quá” | Response/Verification: numeric publication guard hiện có | Guard chữ số không phủ mọi cách viết, không phải chứng minh pháp lý |

Search/EvidenceBuilder không phải lỗi chính của các ca selection đã xem; không thay retrieval/index. Context đủ cấu trúc vẫn chỉ ASSEMBLED_UNVERIFIED. Temporal/reachability chưa kiểm tra không được quy đổi thành SUPPORTED.

## Reproducibility và CI

Team `.python-version` là 3.12. Đã dùng uv 0.13.7, Python3.12.16, `uv sync --frozen --group dev` cài 109 packages từ uv.lock không đổi; `uv pip check` đạt. Từ AI Service root trong checkout đúng của team:

```powershell
uv sync --python 3.12 --frozen --group dev
$env:PYTHONPATH="$pwd"
uv run --frozen pytest -q -m 'not pilot_artifacts'
```

CI không cần model download/API key. Marker pilot_artifacts chỉ các tests phải mở corpus artifact thật. Existing BM25 artifact pin tokenizer Unicode khác Python3.12 (Unicode15.0.0); loader từ chối `incompatible or promoted index` đúng thiết kế. Full suite 3.12 trước marker từng có 116 passed,6 failed,3 skipped,3 errors do mismatch này. Không bypass guard/rebuild index. Runtime corpus đã kiểm là Python3.14.2 của workspace; fresh team deployment phải pin đúng artifact/runtime, hoặc phê duyệt tạo artifact mới riêng.

Từ workspace cha hiện tại (môi trường corpus/cache đã có):

```powershell
$env:PYTHONPATH="$pwd/.tmp/rag-integration-runtime;$pwd/tillegal-ai-main;$pwd"
$env:TILLEGAL_TEST_ML="1"
$env:HF_HUB_OFFLINE="1"
.venv/Scripts/python -B -m pytest -q tillegal-ai-main/tests
.venv/Scripts/python -B -m unittest discover -s tests -q
.venv/Scripts/python -B tillegal-ai-main/scripts/benchmark_context.py --policy context --repeats 3 --output .tmp/context-new.json
.venv/Scripts/python -B tillegal-ai-main/scripts/evaluate_quality.py --labels tillegal-ai-main/.docs/development/m4-results/metric-labels.json --predictions tillegal-ai-main/.docs/development/m4-results/metric-predictions.json --experiment tillegal-ai-main/.docs/development/m4-results/metric-experiment.json --k 2 --output .tmp/metric-new.json
```

Output paths phải mới. Chạy benchmark lần lượt, không đồng thời với ML tests. Windows sandbox chặn asyncio socketpair cần quyền local execution; đây không phải lỗi graph. Không cấu hình Gemini; không cần đọc `.env` hoặc credentials. Final test counts/logs được ghi ở AI_HANDOFF.md.

## Git và bàn giao

Workspace cha là repo BasicRAG, branch main, upstream origin/main, HEAD `825b579cd0d8652d6d07ac3bb17524688ff07b30`, remote `https://github.com/lynkvu2901/Tilligal.git`. `tillegal-ai-main/` là untracked directory không có `.git`; không thể suy ra lịch sử/remote team chỉ từ tên folder. README cha và config/docs untracked là thay đổi có sẵn, giữ nguyên. Không commit/push/merge, không tạo branch trong repo sai.

`package_service_handoff.py` tạo ZIP source/docs/results với per-file SHA256, manifest và incremental patch từ local pre-M4 snapshot. Patch chỉ src/tests/scripts/pyproject vì snapshot trước không chứa docs; ZIP chứa docs hiện tại. Không chứa corpus/model caches, Git metadata hoặc `.env`; source/corpus/cache gốc vẫn giữ nguyên tại workspace. Secret-pattern scan là kiểm tra bổ sung, không phải chứng nhận không có mọi loại secret. Team cần kiểm remote/base thật, tạo `codex/m4-quality-context` trong checkout đó, so hashes before rồi `git apply --check` trước áp dụng; không ghi đè công việc team nếu hashes khác. ZIP là overlay để review, không phải Git history.

## Milestone kế tiếp

Patch đã được áp thử vào bản sao snapshot và khớp SHA256 toàn bộ 16 file thay đổi. Git workspace có `core.autocrlf=true`, nên phải dùng `git -c core.autocrlf=false apply --check m4.patch` rồi `git -c core.autocrlf=false apply m4.patch` trong checkout team đã đối chiếu before hashes để giữ byte hashes. Không sửa Git config toàn cục. ZIP đọc lại từng member và kiểm hash; không chỉ kiểm tra file ZIP tồn tại.

Human review 12 drafts và bổ sung held-out độc lập có điều kiện/ngoại lệ, temporal/version và adversarial numeric claims. Sau đó chạy cùng model local thật trên A/B/C (token budgets, schema failures, latency, unsupported claim rate và abstention); review semantic verdicts độc lập. Đo cross-article evidence recall và false negatives trước khi bật context_judge mặc định. Giải quyết runtime/artifact pin với team trong checkout đúng; không sửa artifact hiện tại để làm test xanh.
