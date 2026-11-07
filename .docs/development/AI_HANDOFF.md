# AI_HANDOFF — Tillegal AI Service

Cập nhật ngày 2026-11-06, múi giờ Asia/Saigon. File này thuộc checkout team tại tillegal-ai-main. Workspace cha là D:/DOWNLOAD/Ligalli Illigal và chứa baseline ai_core cùng artifacts.

## Quy tắc tiếp quản

Đọc file này cùng Git status/diff trước khi sửa code. Sau mỗi milestone hoặc nhóm thay đổi quan trọng, cập nhật trạng thái, file, lệnh kiểm thử, kết quả và bước kế tiếp. Chỉ ghi hoàn thành khi có bằng chứng. Không ghi secrets, API keys hoặc dữ liệu cá nhân.

## Mục tiêu hiện tại

Chốt milestone Real AI Quality & Semantic Citation Verification với evaluation pipeline tái hiện được, real-generation local và verifier có trace. Tiếp tục từ code đang có. Chất lượng pháp lý chưa đủ để chuyển production.

## Đã hoàn thành và bằng chứng

- Đã đọc source và xác minh milestone trước: 102 test service đạt trong 128,96s; 189 test baseline đạt trong 25,761s.
- Audit 12 câu T5 cùng normalized span/raw locator. Cả 12 khớp kỹ thuật; 0/12 có human approval. Không sửa dataset.draft.json. Có guideline và đánh giá từng case trong annotation-quality.md, trace readiness.json.
- Runner retrieval reuse frozen T5 evaluator, bổ sung binary nDCG, latency, missing units. Đã chạy xuyên suốt trên fixture tổng hợp và test phép tính tay. Recall/MRR/nDCG trên corpus thật đang bị chặn bởi human review.
- Thêm workflow draft và semantic trên endpoint pilot. Draft cho phép paraphrase với claim ID và evidence mapping. Semantic dùng evidence gốc, verdict bốn trạng thái, span/version/hash/rationale/usage/latency, fail-closed khi schema/span/provider lỗi.
- Thêm chặn công bố nguồn thiếu danh sách theo sau câu dẫn, biểu mẫu trống và claim làm mất giới hạn số học. Các verdict LLM vẫn được lưu riêng, không đổi thành phán quyết pháp lý.
- Đã tải và kiểm checksum Qwen2.5-1.5B-Instruct Q4_K_M cùng llama.cpp CPU, chạy offline qua 127.0.0.1:18963. Không gọi external API. Hash và lệnh startup ở real-ai-quality.md.
- Đã đo 4 ca exploratory với BasicRAG, multi draft, multi semantic, cả mock/local. Có replay trên đúng draft đã lưu, probe verifier phi pháp lý và hai ca HTTP hậu kiểm. Các trace chứa dữ liệu corpus thử nghiệm và câu hỏi do trợ lý soạn.
- Test bản cuối: 117/117 đạt trong 123,53s. HTTP cuối: một DRAFT và một ABSTAINED; ca thứ hai có LLM SUPPORTED nhưng NUMERIC_BOUND_REQUIRES_REVIEW chặn công bố.
- Báo cáo chính: real-ai-quality.md. Dữ liệu đo: quality-results/*.json.

## Đang làm dở

- Công việc code/test của vertical slice đã chốt. Phần đánh giá chất lượng corpus đang chờ người có chuyên môn review nhãn và câu trả lời.

## Chưa bắt đầu / cần bước riêng

- Chuyên gia duyệt 12 nhãn T5 và scorecard groundedness, relevance, citation correctness.
- Bộ đánh giá độc lập đủ lớn, gắn nhãn điều kiện/ngoại lệ, temporal applicability và source reachability.
- Cải thiện Query/Judge theo kết quả đánh giá độc lập. Chưa sửa retrieval/model/index để tối ưu bốn ca exploratory.
- Đánh giá verifier khác model, concurrency/load/RAM và Python 3.12 theo lockfile team.
- Authentication, ACL, checkpoint resume giữa version, readiness production. Gemini vẫn gated vì chưa xác minh billing/data permission.

## File thay đổi và lý do

Đường dẫn dưới đây tính từ tillegal-ai-main.

- src/applications/tillegal/graphs/semantic.py — generation paraphrase, structured verifier, numeric bounds và publication gate.
- src/applications/tillegal/graphs/multi_agent.py — nối generation/verification mới theo workflow.
- src/applications/tillegal/graphs/legal_qa.py — profile VERIFIER và dispatch mode draft/semantic.
- src/api/routes/chat.py — chấp nhận workflow mới qua schema API.
- src/framework/llm/gateway.py — constrained JSON schema cho provider local, giữ generate thường cho baseline.
- scripts/evaluate_frozen_retrieval.py — nDCG/latency sau checks frozen T5, kiểm lại hash trước scoring.
- scripts/compare_legal_qa.py — so sánh ba workflow, giữ failures/abstention và null cho usage không quan sát.
- scripts/replay_claim_verification.py — tách biến thiên generation khỏi tác động verifier.
- scripts/probe_semantic_verifier.py — ba probe quan hệ văn bản phi pháp lý.
- scripts/score_answer_reviews.py — tính metric sau khi human scorecard đủ và khớp report hash.
- tests/evaluation/test_semantic_quality.py — schema, span, ID, fail-closed, min/max, scorer, nDCG.
- .docs/development/annotation-quality.md, real-ai-quality.md, quality-results/ — guideline, audit và kết quả đo.
- .docs/development/AI_HANDOFF.md — trạng thái tiếp quản liên phiên.

## Git và môi trường

Git root hiện là workspace cha. git status hiển thị README.md đã sửa và config/, docs/, tillegal-ai-main/ untracked. Toàn bộ checkout team đang untracked so với repo cha, vì vậy git diff ở root không hiển thị nội dung các file service. README.md là thay đổi có trước milestone này, đã đọc diff để tránh ghi đè. Không có commit/push của milestone.

Windows CPython 3.14.2. Dependency service thử nghiệm nằm trong .tmp/rag-integration-runtime, baseline dùng .venv. Model local và runtime nằm trong .tmp/quality-llm; giữ ngoài gói source. Không có API key dùng trong test.

## Lệnh test và kết quả gần nhất

Từ workspace root, PowerShell:

```powershell
$env:PYTHONPATH="$pwd/.tmp/rag-integration-runtime;$pwd/tillegal-ai-main;$pwd"
$env:TILLEGAL_TEST_ML="1"
$env:HF_HUB_OFFLINE="1"
.venv/Scripts/python -B -m pytest -q tillegal-ai-main/tests
```

Kết quả cuối 117 passed in 123.53s, đã thu hồi output của session 64181. Bao gồm real retrieval parity trên bốn mode và bốn ca numeric bound mới. Test mô hình sinh dùng fixtures; chạy thật là experiment riêng.

```powershell
$env:TEMP="$pwd/.tmp"
$env:TMP="$pwd/.tmp"
.venv/Scripts/python -B -m unittest discover -s tests -q
```

Kết quả 189 tests in 25.761s, OK, ở đầu milestone. Dòng demo FAILED trong output thuộc test failure-path; exit code cuối 0.

Các phép chạy asyncio/TestClient từng cần escalation do sandbox Windows chặn socketpair. Không xem timeout tạo event loop là lỗi logic ứng dụng.

Lệnh benchmark, replay, probe, frozen scoring và startup ở real-ai-quality.md / annotation-quality.md. File output phải mới. Đã chạy unit nDCG và một frozen synthetic end-to-end qua evaluator baseline, ra Recall=1, MRR=0.5, nDCG=0.6309297536; đây chỉ là fixture tổng hợp.

## Vấn đề chưa giải quyết

- Qwen 1.5B tự tạo số ngày từ biểu mẫu trống; chấm nhầm đối tượng khác là CONTRADICTED; chấm SUPPORTED khi paraphrase bỏ giới hạn “ít nhất”.
- Numeric guard chỉ bắt một số cách biểu đạt bằng chữ số. Không coi guard là semantic verifier hoàn chỉnh.
- Query/Judge rule-based có thể chọn form/chapeau thiếu điều kiện, hoặc không chọn body dù retrieval có hits.
- BasicRAG với cùng model nhỏ thất bại structured output ở ba ca có generation trong benchmark cuối. Lượt sơ bộ có timeout 25s. Chưa sửa baseline.
- Bốn ca exploratory đã được đọc và dùng sửa prompt/gate, không phải held-out. Gold thật vẫn pending. Human metrics là null.
- Latency bị ảnh hưởng cache/CPU; benchmark mới nhất đo trước numeric guard, đã replay kiểm quyết định công bố không đổi.
- Scorer dựa trên attestation human do team quản lý, chưa có hệ thống xác thực người ký review.

## Quyết định kiến trúc

- Giữ BasicRAG và đường basic/multi_agent, thêm draft/semantic cho nghiên cứu.
- Dùng cùng model generation cho ba workflow. Draft/semantic dùng JSON-schema decoding; khác biệt với baseline prompt được công khai.
- Verifier một claim/một source chunk, tối đa ba claims. SUPPORTED là đánh giá textual entailment của model; temporal/reachability/legal validity ghi riêng.
- Không công bố claim bị lỗi integrity, schema, span, thiếu kiểm tra semantic hoặc bị publication gate chặn ở mode semantic.
- Không tự duyệt gold. Freeze/metric corpus phải qua quy trình T5 hiện có.
- Không nâng stack hạ tầng hoặc sửa production.

## Bước tiếp theo cụ thể

1. Đọc handoff, Git status/diff và real-ai-quality.md trước khi bắt đầu nhóm thay đổi tiếp theo.
2. Bàn giao annotation-quality.md cho chuyên gia; chỉ nhận nhãn qua bản sao reviewed rồi freeze, không sửa draft gốc.
3. Dùng score_answer_reviews.py sau khi scorecard độc lập được ký; báo cả coverage/abstention/failures cùng quality.
4. Tạo bộ test nguồn/điều kiện độc lập trước khi cải thiện Judge và lựa chọn context. Chạy lại benchmark bằng artifact mới để giữ lịch sử.

## Nhật ký chốt phiên 2026-11-06

- Đã thu hồi kết quả cuối 117 tests và HTTP DRAFT/ABSTAINED, bổ sung báo cáo numeric-bound guard.
- Đã dừng session llama-server 90998 bằng interrupt sau khi toàn bộ request kết thúc.
- Kiểm tra TCP loopback xác nhận local_runtime_port_closed=True trên cổng 18963.
- Đã kiểm tra file handoff có đủ các mục bắt buộc, đọc lại nội dung và chạy git diff --check.

## Milestone 4 đang triển khai — 2026-11-06

Mục tiêu hiện tại là Evaluation Foundation, Context Selection/Judge và reproducibility. Đã đọc handoff, bốn tài liệu milestone trước, T5/source contracts và Git status/diff.

- Repo cha trên main, tracking origin/main, HEAD 825b579cd0d8652d6d07ac3bb17524688ff07b30. tillegal-ai-main thiếu .git và không có remote team được xác nhận. Chuẩn bị patch/overlay có checksum; chưa tạo lịch sử Git hoặc branch giả.
- Đã giữ source/tests/scripts trước thay đổi và manifest ở .tmp/m4-before, lưu baseline 24 phép đo mock vào m4-results/before.json trước khi sửa graph.
- Đã triển khai feature flag TILLEGAL_CONTEXT_POLICY=legacy|context|context_judge, mặc định legacy. Context chọn nguyên window cùng document version/scope/form/article từ EvidenceBuilder, giữ row và citation identity. Cấu hình context_judge refine bằng heading có thật trong source, dừng khi không có target.
- Đã thêm annotation contract, metric primitives và runner evaluate_quality.py. 26 evaluation tests đạt ở vòng đầu; A/B/C mỗi mode 24 measurements đã chạy.
- Baseline full suite vòng đầu gặp 1 timeout ở Hybrid+Reranker, 116 tests còn lại đạt. Đang kiểm lại parity riêng; không coi lượt này là PASS.
- uv sync --frozen --group dev thành công với Python 3.12.16 và uv.lock hiện có, môi trường riêng .tmp/m4-py312-env.
- Phát hiện Python 3.12 có Unicode 15.0.0, index BM25 được pin tokenizer cho runtime khác. load_index từ chối với incompatible or promoted index. Không đổi artifact hoặc bỏ guard. Cần phân biệt framework CI trên 3.12 với corpus runtime tương thích index.
- Đang làm: final tests, failure analysis A/B, CI guide, handoff package và xác minh checksum/provenance. Quality metrics trên corpus thật vẫn pending human labels.

## Milestone 4 chốt engineering — 2026-11-06

## Tiếp tục real quality — phiên 2026-11-06 đang thực hiện

### Cập nhật vòng2 (ưu tiên trạng thái này so với các bullet khởi đầu bên dưới)

- Baseline real42 requests hoàn tất, `real-quality-results/before/`. Vòng1 real42 hoàn tất, `after-v1/` + `comparison-v1.json`. Vòng cuối đang chạy session26684, `after-final/`, còn final C cases; không chạy thêm LLM requests đồng thời.
- Fixes đã viết: source-grounded heading/participant refinement phục hồi insurance5rows trong mock diagnostic; context titles không citable nhưng giữ visible; strict guards title-only/chapeau/invented numeric/omitted explicit Khi-condition, normalize01=1. Tests target35passed2.55s; sau đó thêm2 reporting tests chưa full-run. Chưa tuyên bố final suite pass.
- Replay guard trên21 previously published real claims chặn mới6 (2numeric,3title,1chapeau), `guard-replay.json`. Không phải human legal error rate. Final B N01 đã chặn con số1 không có trong source dù verifier vẫn SUPPORTED.
- Python3.12 isolated index build + actual HTTP200/DRAFT mock đạt. Hai chiều compatibility312/314 được kiểm với original index/copy; canonical chunks hash bằng nhau. Không đổi artifact gốc.
- Local server session49782/PID10860 vẫn đang chạy; memory sample working1,764,253,696bytes/peak2,232,811,520bytes. Phải shutdown khi xong.
- Tiếp theo: thu hồi session26684, summarize final, real HTTP smoke insurance qua quality_http_smoke.py, full133+new tests với ML thật và189 BasicRAG, frozen3.12 CI, hoàn tất report/handoff/package rồi shutdown.

- Đã đọc yêu cầu mới, handoff, milestone-4, docs trước, Git status/diff. Repo/service boundaries không đổi. Snapshot source/tests/scripts trước sửa ở `.tmp/real-quality-before`.
- Đã xác minh Qwen GGUF SHA256 khớp `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`; llama-server offline localhost18963, ctx8192/threads4/slots1/temp0, exec session49782, log `.tmp/quality-local-server.log`.
- Runner mới `scripts/real_context_quality.py` đang chạy 14 distinct exploratory cases ×3 policies, semantic workflow, top3 BM25, lưu raw model messages/output/usage và full result từng case ở `real-quality-results/before/`, session2210. Không gọi API ngoài, không human gold. Chưa được tuyên bố benchmark hoàn thành.
- Đã tái hiện legacy hallucination10 ngày từ blank form, bị publication gate/span check giữ lại; legacy còn xuất claim về tiền lương làm thêm khi query hỏi sự đồng ý (supported text nhưng answer relevance thấp).
- Điều tra insurance: C refine theo “Chương XII” và hàng loạt heading không liên quan, dùng hết budget; B query bổ sung đạt5 rows. Đang sửa source-grounded heading prioritization, không đổi retrieval.
- Python3.12 tạo index cách ly `.tmp/quality-python312-index` từ original processed snapshot qua builder thật:3085 chunks, index_id bm25:fc5defb4b91aee9be9b62b10537bed4409872c3f6ed0a36a9fa0e5a269119f21. Không đụng index gốc. Cần test load/search/service trên artifact mới và lưu compatibility evidence.
- Chưa hoàn thành: real before/after, fixes/regressions/full tests, HTTP smoke, final handoff/package, shutdown local runtime.

Phần này cập nhật trạng thái mới nhất, thay thế các mục “đang làm” ngay phía trên. Báo cáo chi tiết, công thức metric, failure taxonomy, hướng dẫn annotation/setup và A/B/C ở `milestone-4.md`.

### Mục tiêu và trạng thái

Evaluation pipeline chạy được, context/Judge improvements opt-in, reproducibility và bàn giao an toàn đã triển khai và kiểm thử. Engineering hoàn thành trong phạm vi này; **legal quality validation pending human review**, không có gold được tự phê duyệt. Không gọi API generation bên ngoài, không sửa BasicRAG/retrieval/EvidenceBuilder/index/model revisions/uv.lock.

### Đã hoàn thành và bằng chứng

- Annotation schema v2 phân biệt human_approved/draft/synthetic/exploratory/held_out, canonical source spans, conditions/exceptions, temporal, expected abstention và bốn claim verdicts. Export bản sao 12 T5 draft, kiểm checksum cả ba artifacts gốc không đổi. Không câu nào trở thành gold.
- Metric runner strict inputs, missing-label nulls, retrieval/span/claim/citation/abstention/latency/usage/cost; explicit price metadata; confidence interval chỉ khi đủ independent reviewed cases. Fixtures tính tay và CLI output `m4-results/metric-report-final.json` đạt; không xem synthetic result là legal metric.
- Context layer giữ nguyên window/provenance, kiểm integrity, form intent, following descendants, missing chunks và budget. Test cả false positives/negatives, nhiều versions, cancellation và request isolation. Judge không dùng keyword để kết luận legal SUFFICIENT, chỉ refine từ heading nguồn.
- A/B/C mock mỗi mode 24 measurements trên 8 exploratory cases, cùng BM25 top3. `summary.json`: legacy parity true cho citation identity/call/status trước/sau. A/B/C p50/p95 lần lượt 28.47/44.88,30.76/49.86,18.13/61.22ms; refines24/24/12; abstentions12/12/15. Không có held-out hoặc real-generation A/B trong M4.
- Python3.12.16 uv frozen setup 109 dependencies và pip check đạt. Corpus artifact runtime vẫn Python3.14.2; không bỏ Unicode-tokenizer compatibility guard.
- Git audit: service thiếu .git; parent main/origin-main không phải lịch sử AI Service đã xác nhận. Không commit/branch/push/merge. Source snapshot `.tmp/m4-before`, source/docs/results ZIP và incremental patch đặt tại `outputs/tillegal-m4-handoff/`; manifest chứa hashes trước/sau, team base UNKNOWN.
- Đã kiểm `git apply --check`, áp patch vào bản sao snapshot với `git -c core.autocrlf=false apply`, khớp byte SHA256 cả16 changed files. Git mặc định autocrlf=true đổi line endings, nên không dùng mặc định khi so byte hashes. ZIP được đọc lại từng member để đối chiếu manifest; không chứa caches/model/corpus/.env/Git metadata. Files gốc vẫn giữ tại workspace.

### File thay đổi và lý do

- `src/applications/tillegal/agents/judge/context_selection.py`: context assembly/selection và Judge policy mới.
- `src/applications/tillegal/graphs/{legal_qa,multi_agent,semantic}.py`: workflow flag, timing/trace, mock chọn body thay heading. Default legacy.
- `src/applications/tillegal/evaluation/{annotations,quality_metrics}.py`: validated labels/predictions và scoring primitives.
- `scripts/{evaluate_quality,export_annotation_draft,benchmark_context,summarize_context,package_service_handoff}.py`: runnable scoring/export/benchmark/reproducible handoff.
- `tests/evaluation/{test_quality_metrics,test_context_selection}.py`: hand metrics, fail-closed, intent, cancellation/concurrency regressions.
- `tests/integration/{test_multi_agent,test_pilot_rag}.py`, `pyproject.toml`: marker pilot_artifacts cho corpus-specific tests; không thay dependency lock.
- `.docs/development/milestone-4.md`, `m4-results/*`, file handoff này: báo cáo, inputs/results/checksums và hướng dẫn tiếp quản.

### Lệnh test và kết quả gần nhất

Chạy tại workspace cha, với PYTHONPATH như milestone-4.md:

```powershell
.venv/Scripts/python -B -m pytest -q tillegal-ai-main/tests
# TILLEGAL_TEST_ML=1, HF_HUB_OFFLINE=1: 133 passed in 150.87s
.tmp/m4-py312-env/Scripts/python -B -m pytest -q tillegal-ai-main/tests -m 'not pilot_artifacts'
# 121 passed, 12 deselected in 4.90s, frozen Python3.12; gồm optional price CLI test cuối
.venv/Scripts/python -B -m unittest discover -s tests -q
# 189 tests, OK in 24.612s; demo FAILED là expected failure-path, exit0
```

Logs đã sao chép vào `m4-results/{service-tests,python312-tests,basicrag-tests}.txt`. Full 133 suite khởi chạy trước thay đổi cuối wiring optional price CLI; 121 CI suite chạy sau thay đổi đó và kiểm regression mới. Retrieval parity thật BM25/Dense/Hybrid/Rerank nằm trong full suite. Ruff các file mới/metric/context tests đạt; `git diff --check` đạt cho tracked parent changes. Git không thấy diff service vì toàn thư mục untracked.

Lượt baseline ban đầu 1 timeout Hybrid+Reranker/116 passed khi có công việc khác cạnh tranh CPU vẫn lưu tại `.tmp/m4-before/service-tests.txt`; rerun riêng4 parity tests đạt và hai full runs sau128/133 đạt. Không che failure lịch sử. Python3.12 full corpus suite từng fail vì artifact Unicode mismatch; chỉ framework subset được xác nhận trên3.12.

### Đang làm dở / chưa bắt đầu / vấn đề còn lại

- Không còn implementation/test đang chạy ở M4. Chưa triển khai human annotation adjudication hoặc independent held-out; cần chuyên gia và dataset tách khỏi tuning.
- Chưa chạy real-generation A/B/C với context mới; mock benchmark không chứng minh groundedness/schema adherence/real latency. Real Qwen probes chỉ thuộc milestone trước.
- C tăng abstention và p95, diagnostic insurance B có5 rows còn C không có; giữ opt-in. One-window selection có thể bỏ cross-article exceptions. Không khẳng định heuristics có legal recall cao.
- Semantic verifier còn nhầm entailment/đối tượng; numeric guard chưa phủ số viết bằng chữ. Missing labels/temporal/reachability không được biến thành SUPPORTED.
- Team Git remote/history và artifact/runtime deployment chưa xác nhận. ZIP/patch không thay thế review trên đúng base. Không tạo fake history.

### Quyết định và bước tiếp theo cụ thể

1. Phiên sau đọc file này + milestone-4.md + Git status/diff trước sửa code. Preserve existing parent README/config/docs và artifacts.
2. Nhận reviewed copies của12 T5 records, xác minh reviewer/version/temporal/conditions/exceptions rồi freeze theo annotation-quality.md; không sửa draft gốc.
3. Tạo held-out độc lập trước tiếp tục tune; chạy evaluate_quality.py với predictions đủ cả failures, giữ null cho labels chưa review.
4. Chạy A/B/C cùng local model revision trên reviewed dataset, đo real token/schema/claim failures và conservative false negatives trước đề xuất đổi default.
5. Xác nhận repo team, tạo branch codex/m4-quality-context ở đúng checkout, so before hashes rồi áp patch với autocrlf=false; review overlay docs từ ZIP. Không push/merge nếu chưa yêu cầu.
6. Quyết định pin runtime tương thích artifact hoặc tạo artifact mới riêng theo quy trình team; không tái tạo index ngầm để đạt tests.

## Chốt phiên real local QA — 2026-11-06 (trạng thái mới nhất)

### Mục tiêu / kết quả

Đã tiếp tục M4 bằng chạy thật→debug→sửa→regression→rerun, không dựng lại hệ thống. Báo cáo `real-quality-continuation.md` có paired table, failure taxonomy, source paths, lệnh tái hiện và giới hạn. **Không production-ready**, không human-approved gold mới. Narrow HTTP answer có evidence body đã chạy được; semantic reliability/general legal correctness vẫn chưa đạt mức xác nhận.

### Hoàn thành có bằng chứng

- Local Qwen đúng weights/hash, llama.cpp offline localhost:3 lượt live mỗi lượt14 distinct questions ×3 policies (before,after-v1,after-final), real rerun1 failure cuối và HTTP smoke1. Không cộng lặp thành independent samples. Toàn bộ128 real requests lưu output/trace, cùng corpus BM25 top3/model config; không external model.
- Tái hiện sai số từ blank form, citation vào title, unsupported1/năm, chapeau thiếu list, mất condition và months-vs-years. Không quy tất cả lỗi cho “model yếu”.
- Fix source heading/participant refinement: C insurance từ0 selected lên5 rows, nằm trong budget4. Source titles vẫn visible nhưng không citable; canonical IDs/locators/hash giữ nguyên.
- Guards numeric thiếu source, missing bound, title-only, claim/source colon, blank/source incomplete và explicit Khi/Trừ khi/Cứ...thì. Không đổi SUPPORTED của LLM để giấu lỗi; publication blocker tách riêng. Chuẩn hóa01=1; regression kiểm false reject của parent clause is_heading và điều kiện được giữ.
- Before21 published claims, guard replay chặn6 mới (2numeric/3title/1chapeau); đây không phải human legal error rate. After-final live C có5draft, trong đóN05 “ba tháng/1ngày” vẫn sai nguồn. Đã sửa cuối, replay42 requests với exact saved model messages/schema/completions: C còn4draft/10abstain, chỉN05 đổi. Live rerunN05 cũngABSTAINED8.55s. Không xóa failed trace.
- Actual HTTP `/pilot/legal-qa`200/DRAFT13.18s, câu bảo hiểm xã hội cite body. `real-http.json` có source/version/trace; model SUPPORTED chỉ textual check, legal validity/temporal chưa xác minh.
- Python3.12 index cách ly tạo bằng builder từ original processed snapshot,3085chunks. Source/canonical chunks hash không đổi. Cross-runtime loader kiểm hai chiều; original index giữ Unicode16/Python3.14, isolated index15/Python3.12. HTTP mock3.12 đạt. Không bypass/rebuild/overwrite index production.
- Full source/tests final verified; runtime dừng (session49782/PID10860), port18963 đã xác nhận đóng. Không còn benchmark/test process cần thu hồi.

### Files đã thay đổi và lý do

- `src/applications/tillegal/agents/judge/context_selection.py`:context-v2, rank relevant headings, bounded source-attested participant expansion. Không sửa Query/Search/retriever.
- `src/applications/tillegal/graphs/semantic.py`:context-policy prompt/title alias separation; strict publication guards numeric/title/condition/chapeau, giữ verifier model verdict và trace.
- `scripts/real_context_quality.py`:real paired runner+frozen real-completion replay, strict prompt/schema equality trong replay.
- `scripts/summarize_real_quality.py`:distinct paired cases, taxonomy/latency/usage, incomplete-run rejection, phân biệt live/replay.
- `scripts/replay_publication_guards.py`:deterministic diagnostic trên previously published real claims.
- `scripts/{quality_http_smoke,check_index_runtime}.py`:actual route/no-secret config và nonmutating runtime compatibility reports.
- `tests/evaluation/{test_context_selection,test_semantic_quality,test_real_quality_reporting}.py`:12 tests mới (133→145), source-grounded refinement, alias provenance, guards, incomplete reports.
- `.docs/development/real-quality-continuation.md`, `real-quality-results/*`, handoff:before/after/raw/model logs/results, limitations và commands.

### Test commands và kết quả cuối

Lệnh/env đầy đủ ở report. Source cuối kể cả Cứ...thì:

- `.venv/Scripts/python -B -m pytest -q tillegal-ai-main/tests`, Python3.14.2, `TILLEGAL_TEST_ML=1 HF_HUB_OFFLINE=1`:**145passed184.28s**, full retrieval parity, no exclusions.
- `.tmp/m4-py312-env/Scripts/python -B -m pytest -q tillegal-ai-main/tests -m 'not pilot_artifacts'`:**132passed13deselected5.41s**;13 cần pinned corpus, gồm insurance regression mới. Không tuyên bố full corpus tests trên3.12.
- `.venv/Scripts/python -B -m unittest discover -s tests -q`:**189tests OK26.526s**, expected demo FAILED text không phải suite failure, exit0.
- Target tests trước cuối35passed; full145 bao gồm test bổ sung cuối. Ruff scripts mới/reporting tests đạt. `git diff --check` parent đạt; service untracked nên Git diff không tự bao phủ nó.
- Logs đã sao vào `real-quality-results/{service-tests,python312-tests,basicrag-tests}.txt`.

### Benchmark / kiến trúc / giới hạn

- Before→after live draft counts A4→4,B5→2,C3→5/14; C5 chưa an toàn doN05. Final guard exact replay C4/14, actual rerunN05 abstain. Replay timings/usage là recorded reuse, không phải live inference. Dùng `comparison-live.json` và `comparison-guard-final.json`, không nhầm bản summary sơ bộ `comparison-guard-replay.json` thiếu execution annotations.
- Live p95 A28.39→33.53s,B57.20→22.38s,C57.47→24.56s; C p50 .132→10.58s do thêm generation.14cases/cache/CPU không đủ SLA/CI. Memory llama snapshot working1.764GB/peak2.233GB (decimal), không per-request.
- Default legacy, BasicRAG, retrieval algorithms, EvidenceBuilder, index artifacts, embeddings/model revisions, uv.lock, Supabase schema giữ nguyên. Semantic guards chung tăng cường ở các policy; A after không phải byte-identical baseline, before snapshot mới là baseline bất biến.
- Vẫn thiếu condition/exception coverage human review, independent held-out, cross-article entailment. Model còn output đúng-source nhưng không trả lời đúng ý, false support, paraphrase sai. Heuristic condition literal có thể false-reject paraphrase hợp lệ. Không promote context_judge, không gọi Gemini/paidAPI, không legal gold tự duyệt.

### Git / bàn giao

Parent BasicRAG main/origin-main, HEAD825b579cd0d8652d6d07ac3bb17524688ff07b30; AI Service thiếu.git, untracked. README/config/docs cha có sẵn giữ nguyên. Không commit/branch/push/merge.

Source before ở `.tmp/real-quality-before`. Gói final `outputs/tillegal-real-quality-handoff/` có ZIP source/docs/results, manifest+SHA256SUMS, patch tên `m4.patch` theo packager cũ nhưng base là **pre-real-quality M4 source**,10 incremental files. Đã apply-check và apply trên bản sao snapshot với `git -c core.autocrlf=false apply`, kiểm đúng SHA256 toàn bộ10files. Full ZIP có docs/results; không model/cache/raw corpus/.env/Git. Legal QA raw traces là excerpts local để audit. Không tự áp vào repo team chưa xác nhận remote/base.

### Task dở / chưa bắt đầu / next steps

Không còn implementation/test đang chạy của phiên này. Unresolved product quality không được đánh dấu hoàn tất. Chưa có independent expert review, production integration hoặc model lớn hơn.

1. Phiên sau đọc handoff+real-quality-continuation+Git status/diff. Không chạy lại mọi thứ hoặc ghi đè artifacts.
2. Review raw N01/N02/N05/X07/X08 và failure taxonomy; đánh giá whole-answer relevance/coverage độc lập, nhất là true-source nhưng unrelated answers. Giữ source hash/version identity.
3. Human review12draft và xây held-out riêng; không dùng14cases đã tune để tuyên bố generalization.
4. Tackle cross-article evidence và conditional entailment bằng tests mới độc lập; cân nhắc local model mạnh hơn chỉ sau resource assessment, chưa tự đổi embedding/index hoặc default.
5. Xác nhận team checkout, so before hashes rồi apply patch ở branch codex/ thuộc đúng repo, không push/merge khi chưa yêu cầu. Runtime3.12 chỉ dùng isolated BM25 với explicit TILLEGAL_INDEX, không phối dense index cũ với identity mới.

## Báo cáo đánh giá tổng hợp — 2026-11-06

### Public-source pilot setup — 2026-11-07

Source ZIP 1420063 bytes, Python 3.12 manifest and index only. Local corpus metadata records redistribution rights UNVERIFIED. No corpus redistribution in team Git. pilot_setup now downloads the SHA-pinned public index at Tilligal/825b579, preserves chunks, rebuilds token statistics with the baseline function, requires identical Python 3.12 artifact hash and loads the verified manifest. Qwen download remains pinned; pilot_llama validates binary build and GGUF. README and configs/pilot.env.example give commands. Fresh source copy restored without local index; real HTTP run 018662d8-f269-4eea-8a95-f6d4fda5a54a passed citation smoke. Existing GGUF reused. Docker, Linux/macOS and fresh model download unverified. Next: review local branch against official main and publish only with user approval.

### 2026-11-07 — bootstrap và kiểm thử checkout mới

README có quy trình clone/setup; scripts/pilot_setup.py restore cặp BM25 Python3.12 từ ZIP và verify SHA256 GGUF, có opt-in tải pinned weights; scripts/pilot_socket_smoke.py kiểm provenance qua socket; Compose development chia sẻ loopback API/model. Manifest source cập nhật. ZIP bàn giao riêng outputs/tillegal-pilot-runtime-312/bm25.zip (SHA256 56d82d034a8756289b397e0cd64d90ce9520a60ef26ed46cf9f2fcad66d4a004). Cần team phân phối ZIP hoặc processed snapshot đúng version.

Git archive checkpoint + bootstrap scripts, PYTHONPATH trống, uv sync --offline --frozen --group dev tạo venv mới từ cache; 109 packages. pytest -q: 142 passed, 3 skipped (ML). Startup thiếu index bị từ chối. Socket smoke Qwen/BM25 run 2f8564df-3636-4334-9627-f705889ad1ce PASS; sửa console encoding sau lần đầu. Kiểm metadata remote của GGUF đúng filename/revision, không tải lại model. Docker không có trên máy; config NOT VERIFIED. Next: kiểm Docker, publish artifact qua kênh team, tích hợp diff theo lịch sử chính thức trên branch team rồi kiểm clone thực từ đó. Repo hiện tại vẫn là checkout cá nhân local, không có push hoặc merge.

### Checkpoint Git local — 2026-11-07

AI Service được lưu dưới prefix `tillegal-ai-main/` trên nhánh riêng của repo cha Tilligal, từ base 825b579. Danh mục checkpoint là COMMIT_FILES.txt, gồm cả package RAG và manifest. Git giữ nguyên byte Python trong ai_core để index có thể kiểm tra checksum sau checkout. Raw traces, model và index thuộc gói dữ liệu riêng. Kết quả test gần nhất 142 passed, 3 skipped; công việc tiếp theo là kiểm tra deployment với môi trường mới và Docker.

### Standalone packaging checkpoint (latest implementation; report below is historical)

- User authorized internal ai_core packaging, deployment preparation, independent validation; no Git mutation.
- Backup before edits: parent `.tmp/standalone-before-20261106/tillegal-ai-main`, checksum list `SHA256.json`. Parent baseline preserved. Service still has no team Git metadata; original lead baseline cannot be proven from this checkout.
- Imported ai_core unchanged; wheel now includes src and ai_core. Added source provenance manifest, LF attributes, artifact ignores, pilot environment examples, Docker build exclusions and liveness check, standalone setup guide linked in README.
- Python 3.12 BM25 pair copied into ignored service data directory. No original index modified. Algorithms and provenance unchanged.
- Tests from service root with PYTHONPATH unset: 132 passed/13 deselected (non-corpus); full suite 142 passed/3 skipped (dense/hybrid ML artifacts absent). Isolation/cancellation/backpressure existing regressions included.
- Local Qwen smoke initially failed 504 PROVIDER_TIMEOUT while sandbox runtime was stalled; preserved `data/standalone-local-approved-smoke.json`. After stopping stalled processes and restarting runtime outside sandbox: TestClient real model 200/DRAFT in17.66s, `data/standalone-local-rerun.json`. Actual socket HTTP Uvicorn port18964→Qwen18963: DRAFT, request standalone-socket-user-1, response `data/standalone-socket-http.json`.
- In progress: clean source-copy validation. Still pending: fresh dependency installation/wheel install, final clean-checkout HTTP, Docker execution (docker not found), curated handoff package and exact final commit manifest. Do not mark entire milestone complete yet.
- Update: independent source-copy full suite142passed3skipped23.27s; imports resolved inside copy with PYTHONPATH unset. Copy real-local TestClient smoke200/DRAFT9.59s. Wheel build/install succeeded, SHA256 recorded in standalone-service.md; isolated installed-package import checked. COMMIT_FILES.txt lists candidate service files, excludes caches/data/heavy traces; cannot identify exact delta against unknown lead Git base. Fresh dependency install and Docker/model networking remain pending. Local API/model processes stopped after checks.
- Next: complete packaging validation and docs; separate model/index artifacts. Historic evaluation checksums will no longer match newly edited service files and must not be silently treated as new product results.

- Mục tiêu: bộ AI Evaluation Report cho giảng viên từ artifacts đã lưu, không sửa source sản phẩm hoặc chạy lại model.
- Đã tạo `docs/evaluation/` tại workspace cha: báo cáo tổng hợp tiếng Việt, EVALUATION_SCORECARD, QA_PREDICTIONS_AND_ERRORS.csv, ERROR_ANALYSIS, EVIDENCE_MANIFEST, DEMO_CASE_STUDIES; bổ sung5 PNG charts, JSONL nested records, metric JSON và scripts tái dựng/kiểm tra.
- Chuẩn hóa616 observations từ continuation Qwen, các quality/M4 artifacts (gồm initial trials), T7/T8 và historical demos. Kiểm kê507 artifacts có SHA256. Không coi616 là số câu độc lập. Core14distinct exploratory questions,42requests mỗi phase. LIVE178/REPLAY54/MOCK236/TEST148 tách riêng; historical Claude metadata tách khỏi local Qwen, không gọi external API mới. Sáu T8 mock tool-test records giữ phase riêng với32 benchmark mock records.
- Metrics legal quality thiếu human gold ghi NOT MEASURABLE/PENDING HUMAN REVIEW. Synthetic verifier targets chỉ là fixtures, không legal labels. Citation ID membership/exact span là technical integrity, không citation correctness. Không nâng32provisional T8 labels hoặc12T5 drafts thành gold.
- Phân tích từng14case×3policy và flags toàn dataset,5 case studies giữ nguyên answer/claim/source. Phân biệt đã sửa context, chỉ bị guard chặn, chưa sửa model/semantic và chưa đủ nhãn adjudicate. Chuyển draft→abstain không tự gọi là regression.
- File thay đổi chỉ docs/evaluation/* và handoff này. Không sửa src/tests/uv.lock/index/model, không commit/push/merge. Runners mới nằm trong docs, không import/run ứng dụng.
- Verification: `python docs/evaluation/validate_report.py` kiểm checksum inputs, exact raw answer round-trip, CSV typed values, counts/latency đối chiếu comparison-live, markdown links, và260 product source/test/lock files khớp gói bàn giao trước. Kết quả cuối lưu `docs/evaluation/VALIDATION.json`. CSV được author/round-trip qua artifact-tool;5charts đã xem trực quan. Không chạy lại145/189tests vì không đổi sản phẩm; các test counts trong báo cáo là logs lịch sử đã kiểm kê.
- Không còn task báo cáo đang làm dở sau validation cuối. Human labels, held-out độc lập, cross-article entailment và production readiness vẫn pending như mục trước. Phiên sau đọc handoff+Git status/diff, mở report/scorecard trước khi trích số liệu; không pool replay/mock/live thành accuracy chung.
