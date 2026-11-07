# Real local QA — tiếp tục từ Milestone 4

Đây là thử nghiệm thực thi và sửa source trên corpus pilot; chưa xác nhận legal correctness hay production readiness. Kết quả máy sinh và các đánh giá kỹ thuật dưới đây không phải human-approved gold.

## Đường chạy đã xác minh

`ai_core.basic_rag.BasicRAG.answer` là baseline; `LegalRetrieval` dùng index/retriever gốc. `LegalQA.answer` → `graphs/multi_agent.py` → Query/Search → `agents/judge/context_selection.py` và Judge → `graphs/semantic.py:generate_claims` → `LocalChatProvider` → llama.cpp → `assess`/publication guard → `finish`. HTTP vào `src/api/routes/chat.py:/pilot/legal-qa`, được khởi tạo qua `src/bootstrap.py:create_app` khi pilot development được bật. BasicRAG và default `legacy` giữ nguyên; guards mới áp dụng workflow semantic, không thay basic/multi_agent hoặc thuật toán retrieval.

Đã xác minh weights Qwen2.5-1.5B-Instruct Q4_K_M revision `91cad51170dc346986eccefdc2dd33a9da36ead9`, SHA256 `6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`. Runtime llama.cpp b12125 trên CPU, localhost18963, context8192, threads4, slots1, temperature0; provider max_tokens1024/timeout25s, request deadline60s. Không đổi model/config giữa A/B/C hoặc before/after, không external API. Không đặt seed riêng; cache/scheduling và sai khác generation vẫn ảnh hưởng kết quả. Không coi temp0 là đảm bảo output byte-identical.

## Thiết kế và artifacts

`scripts/real_context_quality.py`: 8 exploratory queries M4 cộng 6 diagnostic queries mới (explicit rights, numeric minimum, conditions/exceptions, multiple provisions, personal ambiguity, future applicability). Tổng14 distinct questions ×3 policies mỗi lượt; các lượt before/after không tạo thêm independent legal samples. Tất cả đã xem trong phát triển nên không phải held-out. Không dùng nhãn T5 để tính chất lượng; 12 T5 vẫn pending human.

`real-quality-results/before/`:42 real semantic requests trên code M4. `after-v1/`:42 requests sau vòng sửa đầu. `after-final/`:lượt cuối. Mỗi file lưu câu hỏi, full result/evidence/version/locator/hash, selected IDs/Judge traces, raw model request/response, citation checks, elapsed time và usage. Manifest lưu index/model/source hashes. Lỗi provider được giữ riêng, raw input vẫn lưu; nếu graph raise thì không có completed graph output, không giả tạo selected/Judge trace cho request lỗi. `condition_exception_review=NOT_EVALUATED` mặc định, human metrics=null.

`scripts/summarize_real_quality.py` kiểm paired case sets và identity, phân loại provider/runtime failure, no evidence, context/Judge abstention, model abstention, verification rejection và experimental draft. Published draft không phải correct answer. Usage thiếu ở request timeout được báo partial, không giả token bằng0. p95 trên14 samples là maximum theo nearest-rank; không có CI chất lượng từ bộ diagnostic nhỏ.

## Debug và fixes có bằng chứng

### Kết quả paired thực tế

| Policy (14 câu mỗi policy) | Before live: draft / abstain / lỗi | After live: draft / abstain / lỗi | p50 trước→sau (s) | p95 trước→sau (s) | Sau guard cuối, replay cùng completions: draft / abstain |
|---|---:|---:|---:|---:|---:|
| A legacy |4 /10 /0|4 /10 /0|.089→.058|28.39→33.53|4 /10|
| B context |5 /8 /1|2 /12 /0|.104→.076|57.20→22.38|2 /12|
| C context_judge |3 /11 /0|5 /9 /0|.132→10.58|57.47→24.56|4 /10|

**Không coi số draft là quality metric.** After-live C có một câu sai quan hệ nguồn N05 vẫn lọt guard; vì vậy không lấy5/14 làm bằng chứng thành công. Đã sửa tiếp, replay đủ42 requests với raw real completions và kiểm messages/schema phải khớp hoàn toàn: riêng C/N05 đổi sang ABSTAINED. Rerun **real local** N05 trên code cuối cũng ABSTAINED (8.55s). Replay có manifest `execution=frozen_real_completions_replay`; timings/usage ở replay không phải chi phí inference mới. Báo cáo đúng loại có ở `comparison-guard-final.json`; `comparison-guard-replay.json` là bản summary sơ bộ trước khi thêm execution annotations, giữ làm lịch sử.

`comparison-live.json` chứa before/after live; `comparison-guard-final.json` chứa delta của guard cuối; `final-live-regression/context_judge-N05.json` chứa real rerun. Code thay đổi lần cuối chỉ guard điều kiện Cứ...thì; không đổi prompt/retrieval giữa after-live và replay. Không thay model/default. A là đối chứng giữ retrieval/selection/generation cũ, nhưng semantic safety guards chung được tăng cường; baseline bất biến thực sự là snapshot và before traces, không khẳng định toàn bộ source A sau sửa byte-identical.

Final published/blocked count theo tầng (current guard, frozen real completions): A7 context/Judge abstentions +3 verifier/publication rejections; B7 context/Judge +5 verifier/publication; C3 context/Judge +1 no-evidence +6 verifier/publication. Before B có1 PROVIDER_TIMEOUT, final live không có provider failures. Không quy tất cả abstention là model yếu; vẫn chưa có nhãn để đo appropriate abstention rate. C p50 tăng vì nhiều câu đi tới generation; p95 giảm là quan sát trên bộ nhỏ/cache/CPU, không phải SLA.

Usage live after:A4553 prompt/1497 completion tokens; B6593/817; C8905/1662. Before B thiếu usage của request timeout nên chỉ có partial reported totals. Không tính cost API bằng0 giả lập: không có API trả phí và estimated cost không đo, local electricity/CPU cost chưa định giá.

### Representative traces và cải thiện kiểm chứng được

- `before/context_judge-X08.json` không có selected context; `after-final/context_judge-X08.json` có5 rows và câu trả lời dựa trên body, không gắn quyền vào title. **Actual HTTP** `real-http.json` trả200/DRAFT sau13.18s với câu “Người lao động phải tham gia bảo hiểm xã hội bắt buộc, bảo hiểm y tế, bảo hiểm thất nghiệp”, cited body + original offsets/hash, semantic SUPPORTED và không blocker. Đây là bản trích nội dung pilot, không xác nhận hiệu lực/áp dụng mọi trường hợp.
- `before/context-N01.json` và `before/context_judge-N01.json` công bố “ít nhất1 lần mỗi năm” từ source không có số; final cả hai bị chặn dù verdict model vẫn SUPPORTED. Có thể quy định đúng nằm ở chỗ khác, nhưng citation này không chứng minh con số.
- `before/context-X07.json` có câu dẫn thiếu danh sách được công bố; final bị chặn. Form blanks không được điền số để tạo answer rate.
- `after-final/context_judge-N05.json` giữ nguyên failure thật: claim ba tháng/1ngày cite “Cứ đủ05 năm...tăng thêm01 ngày”. `final-live-regression/context_judge-N05.json` xác nhận guard cuối chặn. Không xóa trace sai để làm đẹp kết quả.

Guard cuối mở rộng explicit condition thành Khi/Trừ khi/**Cứ...thì**, chuẩn hóa leading zero; regression `test_recurring_year_condition_cannot_be_replaced_by_months` kiểm cả false acceptance và giữ đúng condition. Vẫn có thể false-reject paraphrase đồng nghĩa khác cách viết; trạng thái là requires review, không tự kết luận trái luật.

| Failure tái hiện | Nguyên nhân/source fix | Regression / giới hạn |
|---|---|---|
| C insurance không chọn body, B có5 rows | Refine theo chapter và inherited headings không liên quan; budget hết. `context_selection.py` ưu tiên lexical match của chính heading, giới hạn budget, thêm topic+participant chỉ khi participant có nguyên văn trong retrieved evidence | Tests generic-heading priority, subject provenance/budget, real-corpus insurance recovery. Không đảm bảo retrieval recall trên mọi topic |
| C/B N01 model trả “ít nhất1 lần mỗi năm” và verifier SUPPORTED dù citation chỉ ghi “Số lần, thời gian...” | `semantic.py` chặn numeric value không có trong cited source, vẫn giữ verdict LLM để audit | Test invented99 vs source12; leading zero01=1 được chấp nhận, thiếu “ít nhất” vẫn bị chặn. Chưa chuẩn hóa mọi số viết bằng chữ/đơn vị |
| N02 claim về quyền gắn vào title Điều168 | Model dùng title alias; verifier chấp nhận quá rộng. Đưa title vào context riêng không citable, giữ toàn bộ body và canonical mapping; thêm title publication blocker | Test title visibility/body E1 mapping; substantive parent clauses có is_heading=True không bị loại mù quáng |
| X07 trả câu dẫn “Nội dung chính...bao gồm:” như answer hoàn chỉnh | Guard cũ chỉ xét source kết thúc colon, bỏ sót claim colon. Nay kiểm cả claim | Test permissive verifier vẫn không công bố chapeau |
| Vòngv1 X01 bỏ “Khi nghỉ hằng năm” khỏi claim tạm ứng lương | Guard hẹp giữ literal condition sau Khi/Trừ khi nếu có dấu phân cách; yêu cầu review khi mất | Test mất điều kiện bị chặn, paraphrase “Trong thời gian nghỉ hằng năm” còn giữ condition được phép. Đây là heuristic bảo thủ, không đầy đủ semantic equivalence |
| X03 quote lookup model trả lại tên chủ đề hoặc timeout | Prompt context-policy yêu cầu câu cụ thể, hỗ trợ quote intent, title không phải nguồn claim | Chỉ sửa prompt/serialization, không cắt context/bỏ source để vừa timeout; hiệu quả phải đọc final traces |

Không bỏ publication guard, không chuyển NOT_EVALUATED thành SUPPORTED. Có thể thêm false negatives khi paraphrase số/điều kiện khác cách viết; những trường hợp đó phải review, không khẳng định mô hình sai luật. `assess` vẫn một claim/một cited chunk; cross-article entailment chưa giải quyết.

Replay `guard-replay.json` áp guard hiện tại vào21 claims đã được công bố từ raw before (không sinh lại):6 claims bị chặn mới —2 số không có nguồn,3 title-only evidence,1 câu dẫn. Đây là chẩn đoán kỹ thuật về nguồn được cite, không phải6 legal errors được chuyên gia xác nhận. Full before/after generation được báo riêng; không gộp replay thành kết quả model mới.

## Runtime compatibility đã xử lý ở môi trường cách ly

Index pilot gốc pin Unicode16.0.0; Python3.12.16 dùng15.0.0 và Python3.14.2 dùng16.0.0. Loader so tokenizer contract, không chỉ tên Python. Đã tạo index mới bằng builder thật từ cùng processed snapshot tại `.tmp/quality-python312-index`,3085 chunks, index_id `bm25:fc5defb4b91aee9be9b62b10537bed4409872c3f6ed0a36a9fa0e5a269119f21`. Original index/manifest không sửa, không dùng artifact cách ly cho A/B model.

`compatibility312.json` và `compatibility314.json`:3.12 nhận index cách ly/từ chối index gốc;3.14 nhận index gốc/từ chối index cách ly. Canonical chunk SHA256 cả hai `134a80c6d7db3ff0b1d4bad63129b9af6f92fb3d9fd27352ec954c03084bd6ed`; source/version/locators không đổi. `python312-http.json`:actual FastAPI route200/DRAFT với mock trên index cách ly. Không dùng dense index cũ với BM25 mới vì identity khác.

Contract triển khai: pin Python+Unicode tokenizer+code hashes+index identity đồng bộ. Không bypass validator và không tự chuyển artifact khi mismatch. Lệnh build cách ly (output phải mới):

```powershell
$env:PYTHONPATH="$pwd/tillegal-ai-main;$pwd"
.tmp/m4-py312-env/Scripts/python -B -m ai_core.bm25_retrieval build --manifest data/processed/labor-pilot-3-t3-fix/manifest.json --expected-snapshot 8040db1bfeddb99b93e8937a1c35e634de198a703286318d459d80e90987bfb7 --output-dir .tmp/quality-python312-index-new
.tmp/m4-py312-env/Scripts/python -B tillegal-ai-main/scripts/quality_http_smoke.py --index .tmp/quality-python312-index-new/manifest.json --output .tmp/python312-smoke-new.json
```

## Chạy lại local thật

Từ workspace cha, hai terminal:

```powershell
.tmp/quality-llm/runtime/llama-server.exe -m .tmp/quality-llm/qwen.gguf --host 127.0.0.1 --port 18963 -a qwen-pilot -c 8192 -t 4 -np 1 --temp 0 --offline
```

```powershell
$env:PYTHONPATH="$pwd/.tmp/rag-integration-runtime;$pwd/tillegal-ai-main;$pwd"
.venv/Scripts/python -B tillegal-ai-main/scripts/real_context_quality.py --output .tmp/real-comparison-new
.venv/Scripts/python -B tillegal-ai-main/scripts/quality_http_smoke.py --index data/indexes/labor-pilot-3-t4-bm25/manifest.json --provider local --question 'Trích dẫn: bảo hiểm xã hội' --output .tmp/real-http-new.json
```

Không cần keys/.env. HTTP smoke dùng explicit development settings/database disabled. So sánh before giữ trong repo hoặc chạy source snapshot `.tmp/real-quality-before` với cùng runner; không ghi đè outputs. Chạy model requests tuần tự, không cùng retrieval ML regression. Memory snapshot của llama-server:working set1,764,253,696 bytes, peak2,232,811,520 bytes; đây là process sample trong lượt chạy, không phải per-request allocation.

## Product readiness và việc chưa giải quyết

Engineering có đường chạy thật và guards có regression tests; không suy ra sẵn sàng production từ test xanh. Reproducibility đã có artifact3.12 cách ly và kiểm compatibility hai chiều. Model nhỏ còn false support, wrong citation, unrelated-but-supported answers, bỏ qualifiers và timeout. Một answer DRAFT chỉ qua kiểm textual evidence hạn chế; source reachability/temporal/legal applicability vẫn chưa xác minh.

Không có independent human-reviewed gold. Multi-provision context còn hạn chế: selector giữ một complete window, có thể thiếu cross-article conditions/exceptions; pipeline có thể abstain hoặc trả phần hẹp chưa trả lời hết câu hỏi. Numeric/condition/title heuristics không bảo đảm legal correctness. Chưa promote context_judge/default, chưa đổi production/index/embedding/schema. Bước tiếp theo cần reviewed cases độc lập, coverage của toàn câu hỏi và điều kiện theo source, rồi đánh giá model/verifier mạnh hơn trên local resource được cho phép.

Git vẫn là parent BasicRAG main, service untracked thiếu.git. Không tạo fake history, không commit/push/merge; bảo toàn README/config/docs có sẵn. Bàn giao patch dựa trên local pre-change snapshot và ZIP full source/docs/results, áp ở team checkout đã đối chiếu before hashes.

## Verification cuối và bàn giao

Trên source cuối (kể cả guard Cứ...thì):

```powershell
$env:PYTHONPATH="$pwd/.tmp/rag-integration-runtime;$pwd/tillegal-ai-main;$pwd"
$env:TILLEGAL_TEST_ML='1'
$env:HF_HUB_OFFLINE='1'
.venv/Scripts/python -B -m pytest -q tillegal-ai-main/tests
# Python3.14.2:145 passed in184.28s, gồm BM25/Dense/Hybrid/Rerank parity
$env:PYTHONPATH="$pwd/tillegal-ai-main;$pwd"
.tmp/m4-py312-env/Scripts/python -B -m pytest -q tillegal-ai-main/tests -m 'not pilot_artifacts'
# Python3.12.16 frozen lock:132 passed,13 deselected in5.41s
.venv/Scripts/python -B -m unittest discover -s tests -q
# 189 tests, OK in26.526s
```

Logs ở `real-quality-results/{service-tests,python312-tests,basicrag-tests}.txt`. BasicRAG demo FAILED line là expected failure-path, exit cuối0. Corpus tests không chạy trên index3.12 bằng cách sửa hardcoded test artifacts; compatibility và HTTP smoke trên index cách ly được báo riêng. Ruff các scripts mới/reporting tests đạt. Local llama-server đã dừng, socket localhost18963 được xác minh đóng. Full tests chạy sau inference; CI subset nhẹ chạy cùng full tests, không chạy cùng benchmark inference cuối.

Gói `outputs/tillegal-real-quality-handoff/service-source.zip` chứa source/docs/results; `m4.patch` là tên file từ packager M4, nhưng **base của patch này là snapshot ngay trước phiên real-quality**, không phải pre-M4. Có10 incremental source/test/script files. Đã `git -c core.autocrlf=false apply --check`, áp vào bản sao snapshot và so byte hashes cả10 files; ZIP đọc lại từng member theo manifest. `SHA256SUMS.txt` ghi hash ZIP/patch/manifest. Docs/results nằm trong ZIP overlay vì snapshot incremental không chứa docs. Không chứa model/corpus artifact gốc/.env/cache; raw QA traces chứa trích đoạn corpus để audit, chỉ bàn giao local, không publish. Index3.12 cách ly vẫn nằm `.tmp`, không được promote.

Kết luận thực nghiệm: có narrow real answer chạy qua HTTP với source body, phục hồi context regression và chặn được các failure đã tái hiện; chưa chứng minh chất lượng legal QA tổng quát. Không dùng số tests hoặc số draft làm tiêu chuẩn production readiness.
