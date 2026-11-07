# Annotation và audit nguồn T5

**Trạng thái: 0/12 được người duyệt xác nhận.** Đây là audit kỹ thuật của trợ lý trên snapshot, nhằm chuẩn bị bàn giao. Readiness validator của baseline đã kiểm tra cả hai split. Cả 12 trích đoạn khớp Unicode span trong chunk và locator của raw block theo gói source-first. Chi tiết document_version_id, unit, chunk, số chunk trong Điều và issues nằm ở [readiness.json](quality-results/readiness.json). Toàn bộ nhãn gốc giữ ở PENDING_HUMAN_REVIEW. Test dự kiến T01–T04 không dùng để chạy prediction hoặc sửa prompt.

| Câu | Điều ứng viên trong snapshot | Kết quả rà trước khi duyệt |
|---|---|---|
| D01 | BLLĐ 26 | Có đoạn trực tiếp nhưng attachment HEURISTIC. Cần đối chiếu raw boundary trước khi gắn node Điều. |
| D02 | BLLĐ 25 | Sẵn sàng đưa người duyệt: khoản 2 có ngưỡng và đúng nhóm nghề. Đọc thêm câu dẫn và so với nhóm quản lý ở khoản 1. |
| D03 | BLLĐ 105 | Cần thêm evidence khoản 2 về cách bố trí tuần; nhãn chỉ có khoản 1 sẽ thiếu điều kiện. |
| D04 | BLLĐ 111 | Sẵn sàng đưa người duyệt: cùng span chứa quy tắc và trường hợp chu kỳ lao động đặc biệt. |
| D05 | TT 10, Điều 3 | Sẵn sàng đưa người duyệt: điểm b chứa trường hợp nhiều nơi; cần rà điều luật được dẫn chiếu để chốt tập relevant. |
| D06 | TT 10, Điều 4 | Mở đầu khoản 2 chưa trả lời “gồm những gì”. Source context có các điểm a, b, c, d, đ, e; cần annotate các span danh sách. |
| D07 | NĐ 145, Điều 49 | Câu bị đứt sau chữ “do”, có flag SOURCE_TEXT_POSSIBLY_INCOMPLETE. Đề xuất chuyên gia xét loại hoặc gắn ambiguous cho snapshot. |
| D08 | TT 10, Điều 3 | Có đoạn b1 nhưng parser đánh dấu SUBPOINT_NOT_RESOLVED và ATTACHMENT_REVIEW_REQUIRED. Cần kiểm raw trước khi duyệt địa chỉ chi tiết. |
| T01 | BLLĐ 19 | Sẵn sàng đưa người duyệt: khoản 1 nêu cả quyền và điều kiện thực hiện các hợp đồng. |
| T02 | BLLĐ 90 | Sẵn sàng đưa người duyệt: khoản 3 gồm cả tiêu chí công việc có giá trị như nhau. |
| T03 | BLLĐ 35 | Cần thêm điểm d khoản 1 và khoản 2 cho ngoại lệ. Điểm a khoản 1 chỉ mô tả trường hợp thông thường. |
| T04 | BLLĐ 118 | Sẵn sàng đưa người duyệt: khoản 1 nêu ngưỡng và hình thức văn bản trong cùng đoạn. |

### Quy trình ghi nhãn

1. Người có chuyên môn làm trên bản sao có version. Khi duyệt retrieval, ẩn predictions, rank, prompt và đánh giá AI. Xác nhận đúng snapshot, document_version_id và raw locator; ghi người duyệt, thời điểm và notes. Giữ riêng nhật ký bất đồng, người phân xử và lý do thay đổi nhãn.
2. Xác định loại câu hỏi, chủ thể, điều kiện, ngoại lệ, thời điểm được hỏi. Phân biệt “theo snapshot” với “áp dụng tại ngày X”. Với câu hỏi theo ngày, đối chiếu hiệu lực, sửa đổi và điều khoản chuyển tiếp từ nguồn được phép. Ghi UNKNOWN khi thiếu chứng cứ. Reachability ghi riêng cùng ngày truy cập và nguồn kiểm tra.
3. Article relevance gắn với document_version_id + node Điều. Đọc toàn Điều và rà những đơn vị thay thế/cross-reference trước khi xác nhận tập relevant đầy đủ. Với heading, form, quoted law, heuristic attachment hoặc lỗi raw, ghi rõ loại. Chỉ freeze split khi đủ các cờ review của T5. Không chấm retrieval trên proposed_units.
4. Với mỗi căn cứ, lưu chunk_id, quote hash, exact span [start,end) theo Unicode trên normalized chunk và raw-block locator. Tách span quy tắc chính, điều kiện, ngoại lệ, dẫn chiếu. Raw locator có thể bao cả block; không sử dụng offset normalized để cắt raw HTML.
5. Với câu trả lời, reviewer tách tất cả mệnh đề nội dung, kể cả sai hoặc không dẫn nguồn. Đánh giá mỗi claim chỉ với nguồn đã dẫn: SUPPORTED khi mọi thành phần quan trọng được hỗ trợ; CONTRADICTED khi nguồn khẳng định điều bất tương thích cho cùng đối tượng và phạm vi; INSUFFICIENT_EVIDENCE khi thiếu điều kiện, nguồn im lặng hoặc nói về đối tượng khác. NOT_EVALUATED dành cho phép kiểm tra chưa chạy và không tính thành đúng. Đối chiếu citation correctness riêng (đúng version, đoạn và hỗ trợ claim); một ID tồn tại chưa đủ.
6. Chấm answer relevance theo câu hỏi gốc: câu trả lời phải xử lý ý hỏi, không chỉ lặp chủ đề. Tách các mẫu timeout/schema failure khỏi abstention chủ động. Chấm groundedness ở cấp claim, relevance ở cấp câu trả lời. Đối với claim sai hiệu lực, ghi cả lỗi thời điểm. Đánh giá chéo các ca khó và lưu bất đồng trước khi chốt.
7. Human scorecard cho benchmark: JSON gồm report_sha256, reviewer_type="human", reviewer_id, answers. Mỗi answer có case, mode, relevant (bool), all_material_claims_reviewed=true, claims. Mỗi claim có text nguyên văn từ answer, verdict và citations_correct (bool). Dùng annotation worksheet riêng để lưu ID/span/lý do và temporal/reachability trước khi xuất scorecard. Scorer từ chối bộ thiếu answer, claim lặp và checksum sai. Các trường reviewer là attestation của người nhập; quyền ký duyệt do team quản lý.

### Chạy retrieval evaluation

Dùng workspace Python/PYTHONPATH trong pilot-rag.md, gồm checkout có module T5 ai_core.retrieval_evaluation. Dùng lệnh freeze gốc trên **bản đã duyệt**, rồi chạy script mở rộng trong service:

```powershell
.venv/Scripts/python -m ai_core.retrieval_evaluation freeze --dataset <reviewed.json> --index-manifest <bm25-manifest> --split dev --output-dir <new-frozen-directory>
.venv/Scripts/python tillegal-ai-main/scripts/evaluate_frozen_retrieval.py --frozen <frozen-manifest> --index <bm25-manifest> --output <new-results-directory>
```

Runner dùng lại chính sách dedup và unresolved slots, kiểm hash dataset/index/code của baseline. Tính macro Recall@5/@10, MRR@5/@10, binary nDCG@5/@10 theo Điều, danh sách đơn vị bị bỏ lỡ và latency retrieval trong từng query, median toàn split. Heading đúng Điều có thể ghi điểm discovery dù evidence thiếu ngoại lệ. Đánh giá đó cần annotation cấp span ở bước riêng.
