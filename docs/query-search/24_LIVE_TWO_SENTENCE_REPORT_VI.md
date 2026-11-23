# Báo cáo chạy thật Query → Search: hai câu

Tôi ký hợp đồng lao động thời hạn 24 tháng và đã làm việc được 6 tháng, nay muốn nghỉ việc để chuyển sang công ty khác. Tôi phải báo trước bao lâu và nếu nghỉ ngay thì có thể phải bồi thường những khoản nào?

Khởi chạy Gemini thật, Search BM25 trên Supabase chỉ đọc. Facts là lời người dùng, không phải sự thật đã xác minh.

## Query nhận và trả gì

Model gemini-3.5-flash-lite; latency 7134.28 ms. Nhận nguyên văn câu hỏi; trả plan dưới đây. Issues là nhu cầu tìm kiếm, không phải kết luận pháp lý.

```json
{
  "original": "Tôi ký hợp đồng lao động thời hạn 24 tháng và đã làm việc được 6 tháng, nay muốn nghỉ việc để chuyển sang công ty khác. Tôi phải báo trước bao lâu và nếu nghỉ ngay thì có thể phải bồi thường những khoản nào?",
  "intent": "legal_question",
  "domain": "labour",
  "temporal_scope": [
    "24 tháng",
    "6 tháng"
  ],
  "subqueries": [
    {
      "text": "người lao động ký hợp đồng lao động xác định thời hạn đơn phương chấm dứt hợp đồng phải báo trước bao lâu; tình huống người dùng: Tôi ký hợp đồng lao động thời hạn 24 tháng; đã làm việc được 6 tháng; nay muốn nghỉ việc để chuyển sang công ty khác",
      "purpose": "question_part"
    },
    {
      "text": "người lao động đơn phương chấm dứt hợp đồng lao động trái pháp luật phải bồi thường những khoản gì; tình huống người dùng: Tôi ký hợp đồng lao động thời hạn 24 tháng; đã làm việc được 6 tháng; nay muốn nghỉ việc để chuyển sang công ty khác",
      "purpose": "question_part"
    }
  ],
  "clarification": null,
  "analysis_method": "llm",
  "analysis_model": "gemini-3.5-flash-lite",
  "facts": [
    {
      "text": "Tôi ký hợp đồng lao động thời hạn 24 tháng",
      "source_quote": "Tôi ký hợp đồng lao động thời hạn 24 tháng"
    },
    {
      "text": "đã làm việc được 6 tháng",
      "source_quote": "đã làm việc được 6 tháng"
    },
    {
      "text": "nay muốn nghỉ việc để chuyển sang công ty khác",
      "source_quote": "nay muốn nghỉ việc để chuyển sang công ty khác"
    }
  ],
  "issues": [
    "Thời hạn báo trước khi người lao động đơn phương chấm dứt hợp đồng lao động xác định thời hạn",
    "Nghĩa vụ bồi thường của người lao động khi đơn phương chấm dứt hợp đồng lao động trái pháp luật hoặc các khoản phải bồi thường khi nghỉ việc"
  ],
  "missing_information": [
    "Bạn muốn nghỉ việc vì lý do gì?",
    "Có thỏa thuận đào tạo hoặc hoàn trả chi phí đào tạo không?"
  ],
  "citations": [],
  "temporal_context": [
    {
      "text": "24 tháng",
      "start": 34,
      "end": 42,
      "role": "duration",
      "iso_date": null,
      "negated": false
    },
    {
      "text": "6 tháng",
      "start": 63,
      "end": 70,
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

## Search thực thi

Status COMPLETED; completeness COMPLETE; backend calls 2; nhóm evidence 6; latency 5201.74 ms.

Options do caller cấp: {"mode": "bm25", "top_k": 5, "as_of_date": "2026-11-23", "allowed_usage_policies": ["EXPERIMENTAL_ONLY"]}

Rank tính riêng cho mỗi query. raw_score là điểm BM25, không phải xác suất đúng; không so trực tiếp giữa các query. COMPLETE chỉ nói thực thi đủ lượt, không nói đủ căn cứ pháp lý.

### Query 0: người lao động ký hợp đồng lao động xác định thời hạn đơn phương chấm dứt hợp đồng phải báo trước bao lâu; tình huống người dùng: Tôi ký hợp đồng lao động thời hạn 24 tháng; đã làm việc được 6 tháng; nay muốn nghỉ việc để chuyển sang công ty khác
Status OK; index vbpl-bm25-unicode-v1; request_id 6770eeb1-92d5-4cb8-b827-16f48824656f.

|Rank|BM25 score|Nguồn|Chunk ID|
|---|---|---|---|
|1|41.1625445045701|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|01fcd190-2fc8-48ee-8cf5-de8fc77fada7|
|2|39.1581494722179|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|30142e55-42ce-494a-a6fe-a8a10eb46922|
|3|36.0295300011835|Nghị định 369/2026/NĐ-CP của Chính phủ|b6c170cb-de6d-42df-a79b-479251439db6|
|4|33.40624818458|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|758fd1e3-72be-44e5-b4de-a55bd2b26a15|
|5|33.2157666238166|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|2973a693-2276-4e4f-a233-f7038e4717e0|

#### Rank 1: Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk
Source ID 60c5be9f-20d9-4897-977e-2059f2c59ff2; node chapter-i-article-5-clause-1-point-c; chunk_key legal-v2-block-000060-1.
issued_on 2026-10-20; effective_from 2026-10-30; effective_to None.
URL: https://vbpl.vn/van-ban/chi-tiet/nghi-quyet-so-25-2026-nq-hdnd-quy-dinh-chinh-sach-thu-hut-ho-tro-dao-tao-phat-trien-nguon-nhan-luc-cua-tinh-dak-lak-giai-doan-2026-2031--177c1650-dc18-11f1-a2f3-6f4db9961316
Hash 1acec948dd7ee1d1e35e7b4a1ed9c4a3ba4ed5986917bf51eb9b9683d269c9e5; MATCHED_STORED.

```text
Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk > Chương I > Điều 5: Hoàn trả kinh phí hỗ trợ thu hút, đào tạo > Khoản 1 > Điểm c > 1. Người được thu hút thông qua hình thức tuyển dụng, tiếp nhận vào làm công chức, viên chức hoặc hình thức hợp đồng lao động xác định thời hạn phải hoàn trả 100% mức hỗ trợ ban đầu và thu nhập theo lợi nhuận hoặc giá trị công trình nêu tại khoản 1, khoản 2 Điều 7 và điểm a khoản 1 Điều 8 Nghị quyết này; người được hưởng chính sách hỗ trợ đào tạo phải hoàn trả 100% mức hỗ trợ nêu tại Điều 10 Nghị quyết này, nếu thuộc một trong các trường hợp sau:

c) Người được thu hút thông qua hình thức tuyển dụng, tiếp nhận vào làm công chức, viên chức hoặc người được hưởng chính sách hỗ trợ đào tạo xin thôi việc hoặc xin chuyển công tác ra ngoài hệ thống các cơ quan, đơn vị của tỉnh nhưng có thời gian làm việc chưa đủ 1/2 (một phần hai) thời gian đã cam kết; người được thu hút thông qua hình thức hợp đồng lao động xác định thời hạn chưa hoàn thành thời hạn hợp đồng lao động đã ký kết hoặc tham gia các thỏa thuận, giao dịch khác gây ảnh hưởng tiêu cực đến việc thực hiện các nội dung trong hợp đồng đã ký kết.
```

#### Rank 2: Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk
Source ID 60c5be9f-20d9-4897-977e-2059f2c59ff2; node chapter-ii-article-8-clause-1-point-b; chunk_key legal-v2-block-000114-1.
issued_on 2026-10-20; effective_from 2026-10-30; effective_to None.
URL: https://vbpl.vn/van-ban/chi-tiet/nghi-quyet-so-25-2026-nq-hdnd-quy-dinh-chinh-sach-thu-hut-ho-tro-dao-tao-phat-trien-nguon-nhan-luc-cua-tinh-dak-lak-giai-doan-2026-2031--177c1650-dc18-11f1-a2f3-6f4db9961316
Hash becaa0e186697f1d7b2e880cb5e24aceff553240fb7548a80f9c090e10a7a9df; MATCHED_STORED.

```text
Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk > Chương II > Điều 8: Chính sách đối với người được thu hút theo hình thức hợp đồng lao động xác định thời hạn > Khoản 1 > Điểm b > 1. Đối tượng quy định tại các điểm c, d và đ khoản 1 Điều 2 Nghị quyết đáp ứng các tiêu chuẩn, điều kiện tại các khoản 1, 2, 3, 4 và 6 Điều 6 Nghị quyết này được thu hút theo hình thức hợp đồng lao động xác định thời hạn tại các cơ quan, đơn vị của tỉnh được hưởng các chính sách sau:

b) Chính sách tiền lương

Được ký kết hợp đồng lao động xác định thời hạn với mức lương tối đa 100 triệu đồng/người/tháng. Mức lương này đã bao gồm tiền lương hàng tháng, các khoản phụ cấp kèm theo lương (nếu có), các khoản đóng bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp và các loại bảo hiểm khác theo quy định của pháp luật.
```

#### Rank 3: Nghị định 369/2026/NĐ-CP của Chính phủ
Source ID 450304fc-b390-46bc-8994-4fc8ba485c55; node article-3-clause-1; chunk_key legal-v2-block-000021-1.
issued_on 2026-09-25; effective_from 2026-11-11; effective_to None.
URL: https://vbpl.vn/van-ban/chi-tiet/nghi-dinh-so-369-2026-nd-cp-sua-doi-bo-sung-mot-so-dieu-cua-nghi-dinh-so-155-2025-nd-cp-ngay-16-thang-6-nam-2025-cua-chinh-phu-quy-dinh-tieu-chuan-dinh-muc-su-dung-tru-so-lam-viec-co-so-hoat-dong-su-nghiep--25f863d0-bd43-11f1-887c-5fb19e26c115
Hash 7b72bdb27b9e9e64fe6ce68478e0421882c304d57ac840305cf2a40c884472e6; MATCHED_STORED.

```text
Nghị định 369/2026/NĐ-CP của Chính phủ > Điều 3: Bổ sung Điều 3a > Khoản 1 > 1. Đối với trường hợp thực hiện sáp nhập, hợp nhất, chia tách, chấm dứt hoạt động; cơ quan quản lý cấp trên của cơ quan, tổ chức, đơn vị được giao quản lý, sử dụng tài sản bị giải thể, chấm dứt hoạt động:

Cơ quan, tổ chức, đơn vị được kế thừa quyền quản lý, sử dụng trụ sở làm việc, cơ sở hoạt động sự nghiệp sau khi sáp nhập, hợp nhất; được giao quản lý, sử dụng trụ sở làm việc, cơ sở hoạt động sự nghiệp theo đề án/phương án chia tách được cấp có thẩm quyền phê duyệt; được tiếp nhận trụ sở làm việc, cơ sở hoạt động sự nghiệp theo đề án/phương án sắp xếp bộ máy được cấp có thẩm quyền phê duyệt; được tiếp tục quản lý, sử dụng trụ sở làm việc, cơ sở hoạt động sự nghiệp sau khi chuyển sang trực thuộc cơ quan quản lý cấp trên khác (sau đây gọi chung là cơ quan, tổ chức, đơn vị tiếp nhận) có trách nhiệm tiếp nhận nguyên trạng trụ sở làm việc, cơ sở hoạt động sự nghiệp. Trong thời hạn 06 tháng, kể từ ngày tiếp nhận, cơ quan, tổ chức, đơn vị tiếp nhận có trách nhiệm rà soát để xử lý theo quy định tại khoản 2, khoản 3 Điều này.
```

#### Rank 4: Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk
Source ID 60c5be9f-20d9-4897-977e-2059f2c59ff2; node chapter-i-article-5-clause-3; chunk_key legal-v2-block-000068-1.
issued_on 2026-10-20; effective_from 2026-10-30; effective_to None.
URL: https://vbpl.vn/van-ban/chi-tiet/nghi-quyet-so-25-2026-nq-hdnd-quy-dinh-chinh-sach-thu-hut-ho-tro-dao-tao-phat-trien-nguon-nhan-luc-cua-tinh-dak-lak-giai-doan-2026-2031--177c1650-dc18-11f1-a2f3-6f4db9961316
Hash 239eeba4a74b55f8bb5a12e5dc0357753d6e2365408cc948eb742b1db507f831; MATCHED_STORED.

```text
Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk > Chương I > Điều 5: Hoàn trả kinh phí hỗ trợ thu hút, đào tạo > Khoản 3 > 3. Mức hoàn trả kinh phí hỗ trợ

Người được thu hút thông qua hình thức tuyển dụng, tiếp nhận vào làm công chức, viên chức hoặc hình thức hợp đồng lao động xác định thời hạn; người được hưởng chính sách hỗ trợ đào tạo thuộc các trường hợp quy định tại khoản 2 Điều này có trách nhiệm hoàn trả một phần kinh phí hỗ trợ ban đầu hoặc hỗ trợ đào tạo. Mức hoàn trả kinh phí hỗ trợ được tính theo công thức sau:

S = (F / T1) × (T1 - T2)

Trong đó:

S là mức hoàn trả kinh phí hỗ trợ;

F là kinh phí hỗ trợ ban đầu được cấp cho người được thu hút nêu tại khoản 1 Điều 7 và điểm a khoản 1 Điều 8 Nghị quyết này hoặc kinh phí hỗ trợ đào tạo được cấp cho người hưởng chính sách hỗ trợ đào tạo nêu tại Điều 10 Nghị quyết này;

T1 là số tháng làm việc đã cam kết theo quy định tại khoản 5 Điều 6 Nghị quyết này hoặc số tháng làm việc theo thời hạn hợp đồng lao động đã ký kết hoặc số tháng làm việc đã cam kết theo quy định tại khoản 5 Điều 9 Nghị quyết này;

T2 là số tháng đã làm việc thực tế tại các cơ quan, đơn vị của tỉnh sau khi được thu hút hoặc đào tạo (được tính tròn tháng nếu số ngày làm việc trong tháng từ 15 ngày trở lên).
```

#### Rank 5: Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk
Source ID 60c5be9f-20d9-4897-977e-2059f2c59ff2; node chapter-i-article-5-clause-2-point-b; chunk_key legal-v2-block-000066-1.
issued_on 2026-10-20; effective_from 2026-10-30; effective_to None.
URL: https://vbpl.vn/van-ban/chi-tiet/nghi-quyet-so-25-2026-nq-hdnd-quy-dinh-chinh-sach-thu-hut-ho-tro-dao-tao-phat-trien-nguon-nhan-luc-cua-tinh-dak-lak-giai-doan-2026-2031--177c1650-dc18-11f1-a2f3-6f4db9961316
Hash f77a5da81f5d0c518f4fb61754300b17dfc0909d412430e3f976e503bd04e396; MATCHED_STORED.

```text
Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk > Chương I > Điều 5: Hoàn trả kinh phí hỗ trợ thu hút, đào tạo > Khoản 2 > Điểm b > 2. Người được thu hút thông qua hình thức tuyển dụng, tiếp nhận vào làm công chức, viên chức hoặc hình thức hợp đồng lao động xác định thời hạn phải hoàn trả một phần mức hỗ trợ ban đầu nêu tại khoản 1 Điều 7 và điểm a khoản 1 Điều 8 Nghị quyết này theo mức quy định tại khoản 3 Điều này và 100% mức thu nhập theo lợi nhuận hoặc giá trị công trình nêu tại khoản 2 Điều 7 Nghị quyết này; người được hưởng chính sách hỗ trợ đào tạo phải hoàn trả một phần mức hỗ trợ nêu tại Điều 10 Nghị quyết này theo mức quy định tại khoản 3 Điều này nếu thuộc một trong các trường hợp sau (trừ các trường hợp nêu tại khoản 1 Điều này):

b) Đơn phương chấm dứt hợp đồng lao động theo quy định tại khoản 2 Điều 35 Bộ luật Lao động số 45/2019/QH14.
```

### Query 1: người lao động đơn phương chấm dứt hợp đồng lao động trái pháp luật phải bồi thường những khoản gì; tình huống người dùng: Tôi ký hợp đồng lao động thời hạn 24 tháng; đã làm việc được 6 tháng; nay muốn nghỉ việc để chuyển sang công ty khác
Status OK; index vbpl-bm25-unicode-v1; request_id 8da62a04-9455-4966-8b20-817e023ad077.

|Rank|BM25 score|Nguồn|Chunk ID|
|---|---|---|---|
|1|38.5842878381402|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|01fcd190-2fc8-48ee-8cf5-de8fc77fada7|
|2|35.9311858285454|Nghị định 369/2026/NĐ-CP của Chính phủ|b6c170cb-de6d-42df-a79b-479251439db6|
|3|35.6693200513719|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|30142e55-42ce-494a-a6fe-a8a10eb46922|
|4|32.612903668669|Văn bản hợp nhất 01/2026/VBHN-NĐ-BNG của Văn phòng Chính phủ|d7f358eb-2586-42c5-9c7d-d2b9f228ca91|
|5|32.326739494673|Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk|2973a693-2276-4e4f-a233-f7038e4717e0|

#### Rank 1: Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk
Source ID 60c5be9f-20d9-4897-977e-2059f2c59ff2; node chapter-i-article-5-clause-1-point-c; chunk_key legal-v2-block-000060-1.
issued_on 2026-10-20; effective_from 2026-10-30; effective_to None.
URL: https://vbpl.vn/van-ban/chi-tiet/nghi-quyet-so-25-2026-nq-hdnd-quy-dinh-chinh-sach-thu-hut-ho-tro-dao-tao-phat-trien-nguon-nhan-luc-cua-tinh-dak-lak-giai-doan-2026-2031--177c1650-dc18-11f1-a2f3-6f4db9961316
Hash 1acec948dd7ee1d1e35e7b4a1ed9c4a3ba4ed5986917bf51eb9b9683d269c9e5; MATCHED_STORED.

```text
Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk > Chương I > Điều 5: Hoàn trả kinh phí hỗ trợ thu hút, đào tạo > Khoản 1 > Điểm c > 1. Người được thu hút thông qua hình thức tuyển dụng, tiếp nhận vào làm công chức, viên chức hoặc hình thức hợp đồng lao động xác định thời hạn phải hoàn trả 100% mức hỗ trợ ban đầu và thu nhập theo lợi nhuận hoặc giá trị công trình nêu tại khoản 1, khoản 2 Điều 7 và điểm a khoản 1 Điều 8 Nghị quyết này; người được hưởng chính sách hỗ trợ đào tạo phải hoàn trả 100% mức hỗ trợ nêu tại Điều 10 Nghị quyết này, nếu thuộc một trong các trường hợp sau:

c) Người được thu hút thông qua hình thức tuyển dụng, tiếp nhận vào làm công chức, viên chức hoặc người được hưởng chính sách hỗ trợ đào tạo xin thôi việc hoặc xin chuyển công tác ra ngoài hệ thống các cơ quan, đơn vị của tỉnh nhưng có thời gian làm việc chưa đủ 1/2 (một phần hai) thời gian đã cam kết; người được thu hút thông qua hình thức hợp đồng lao động xác định thời hạn chưa hoàn thành thời hạn hợp đồng lao động đã ký kết hoặc tham gia các thỏa thuận, giao dịch khác gây ảnh hưởng tiêu cực đến việc thực hiện các nội dung trong hợp đồng đã ký kết.
```

#### Rank 2: Nghị định 369/2026/NĐ-CP của Chính phủ
Source ID 450304fc-b390-46bc-8994-4fc8ba485c55; node article-3-clause-1; chunk_key legal-v2-block-000021-1.
issued_on 2026-09-25; effective_from 2026-11-11; effective_to None.
URL: https://vbpl.vn/van-ban/chi-tiet/nghi-dinh-so-369-2026-nd-cp-sua-doi-bo-sung-mot-so-dieu-cua-nghi-dinh-so-155-2025-nd-cp-ngay-16-thang-6-nam-2025-cua-chinh-phu-quy-dinh-tieu-chuan-dinh-muc-su-dung-tru-so-lam-viec-co-so-hoat-dong-su-nghiep--25f863d0-bd43-11f1-887c-5fb19e26c115
Hash 7b72bdb27b9e9e64fe6ce68478e0421882c304d57ac840305cf2a40c884472e6; MATCHED_STORED.

```text
Nghị định 369/2026/NĐ-CP của Chính phủ > Điều 3: Bổ sung Điều 3a > Khoản 1 > 1. Đối với trường hợp thực hiện sáp nhập, hợp nhất, chia tách, chấm dứt hoạt động; cơ quan quản lý cấp trên của cơ quan, tổ chức, đơn vị được giao quản lý, sử dụng tài sản bị giải thể, chấm dứt hoạt động:

Cơ quan, tổ chức, đơn vị được kế thừa quyền quản lý, sử dụng trụ sở làm việc, cơ sở hoạt động sự nghiệp sau khi sáp nhập, hợp nhất; được giao quản lý, sử dụng trụ sở làm việc, cơ sở hoạt động sự nghiệp theo đề án/phương án chia tách được cấp có thẩm quyền phê duyệt; được tiếp nhận trụ sở làm việc, cơ sở hoạt động sự nghiệp theo đề án/phương án sắp xếp bộ máy được cấp có thẩm quyền phê duyệt; được tiếp tục quản lý, sử dụng trụ sở làm việc, cơ sở hoạt động sự nghiệp sau khi chuyển sang trực thuộc cơ quan quản lý cấp trên khác (sau đây gọi chung là cơ quan, tổ chức, đơn vị tiếp nhận) có trách nhiệm tiếp nhận nguyên trạng trụ sở làm việc, cơ sở hoạt động sự nghiệp. Trong thời hạn 06 tháng, kể từ ngày tiếp nhận, cơ quan, tổ chức, đơn vị tiếp nhận có trách nhiệm rà soát để xử lý theo quy định tại khoản 2, khoản 3 Điều này.
```

#### Rank 3: Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk
Source ID 60c5be9f-20d9-4897-977e-2059f2c59ff2; node chapter-ii-article-8-clause-1-point-b; chunk_key legal-v2-block-000114-1.
issued_on 2026-10-20; effective_from 2026-10-30; effective_to None.
URL: https://vbpl.vn/van-ban/chi-tiet/nghi-quyet-so-25-2026-nq-hdnd-quy-dinh-chinh-sach-thu-hut-ho-tro-dao-tao-phat-trien-nguon-nhan-luc-cua-tinh-dak-lak-giai-doan-2026-2031--177c1650-dc18-11f1-a2f3-6f4db9961316
Hash becaa0e186697f1d7b2e880cb5e24aceff553240fb7548a80f9c090e10a7a9df; MATCHED_STORED.

```text
Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk > Chương II > Điều 8: Chính sách đối với người được thu hút theo hình thức hợp đồng lao động xác định thời hạn > Khoản 1 > Điểm b > 1. Đối tượng quy định tại các điểm c, d và đ khoản 1 Điều 2 Nghị quyết đáp ứng các tiêu chuẩn, điều kiện tại các khoản 1, 2, 3, 4 và 6 Điều 6 Nghị quyết này được thu hút theo hình thức hợp đồng lao động xác định thời hạn tại các cơ quan, đơn vị của tỉnh được hưởng các chính sách sau:

b) Chính sách tiền lương

Được ký kết hợp đồng lao động xác định thời hạn với mức lương tối đa 100 triệu đồng/người/tháng. Mức lương này đã bao gồm tiền lương hàng tháng, các khoản phụ cấp kèm theo lương (nếu có), các khoản đóng bảo hiểm xã hội, bảo hiểm y tế, bảo hiểm thất nghiệp và các loại bảo hiểm khác theo quy định của pháp luật.
```

#### Rank 4: Văn bản hợp nhất 01/2026/VBHN-NĐ-BNG của Văn phòng Chính phủ
Source ID 1632d7cb-fb66-4389-b91b-820809e1432d; node chapter-ii-article-10-clause-2; chunk_key legal-v2-block-000085-1.
issued_on 2026-11-09; effective_from None; effective_to None.
URL: https://vbpl.vn/van-ban/chi-tiet/van-ban-hop-nhat-quy-dinh-mot-so-che-do-doi-voi-thanh-vien-co-quan-viet-nam-o-nuoc-ngoai-so-01-2026-vbhn-nd-bng--bf9aabf0-dca7-11f1-840b-97c0d7c724be
Hash b023b4ce53834256df72d46ee0e19e71c1828a62754653a898acfdf1fdebd0cb; MATCHED_STORED.

```text
Văn bản hợp nhất 01/2026/VBHN-NĐ-BNG của Văn phòng Chính phủ > Chương II > Điều 10: Thời gian làm việc và chế độ nghỉ ngơi > Khoản 2 > 2. Thành viên cơ quan Việt Nam ở nước ngoài được nghỉ hưởng nguyên sinh hoạt phí trong những ngày nghỉ hằng năm, nghỉ ngày lễ, Tết, nghỉ việc riêng theo quy định của pháp luật về lao động và trong những ngày nghỉ lễ chính thức của nước sở tại.
```

#### Rank 5: Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk
Source ID 60c5be9f-20d9-4897-977e-2059f2c59ff2; node chapter-i-article-5-clause-2-point-b; chunk_key legal-v2-block-000066-1.
issued_on 2026-10-20; effective_from 2026-10-30; effective_to None.
URL: https://vbpl.vn/van-ban/chi-tiet/nghi-quyet-so-25-2026-nq-hdnd-quy-dinh-chinh-sach-thu-hut-ho-tro-dao-tao-phat-trien-nguon-nhan-luc-cua-tinh-dak-lak-giai-doan-2026-2031--177c1650-dc18-11f1-a2f3-6f4db9961316
Hash f77a5da81f5d0c518f4fb61754300b17dfc0909d412430e3f976e503bd04e396; MATCHED_STORED.

```text
Nghị quyết 25/2026/NQ-HĐND của HĐND Tỉnh Đắk Lắk > Chương I > Điều 5: Hoàn trả kinh phí hỗ trợ thu hút, đào tạo > Khoản 2 > Điểm b > 2. Người được thu hút thông qua hình thức tuyển dụng, tiếp nhận vào làm công chức, viên chức hoặc hình thức hợp đồng lao động xác định thời hạn phải hoàn trả một phần mức hỗ trợ ban đầu nêu tại khoản 1 Điều 7 và điểm a khoản 1 Điều 8 Nghị quyết này theo mức quy định tại khoản 3 Điều này và 100% mức thu nhập theo lợi nhuận hoặc giá trị công trình nêu tại khoản 2 Điều 7 Nghị quyết này; người được hưởng chính sách hỗ trợ đào tạo phải hoàn trả một phần mức hỗ trợ nêu tại Điều 10 Nghị quyết này theo mức quy định tại khoản 3 Điều này nếu thuộc một trong các trường hợp sau (trừ các trường hợp nêu tại khoản 1 Điều này):

b) Đơn phương chấm dứt hợp đồng lao động theo quy định tại khoản 2 Điều 35 Bộ luật Lao động số 45/2019/QH14.
```

## Cảnh báo, lỗi và provenance

```json
{
  "warnings": [
    "TEMPORAL_METADATA_INCOMPLETE",
    "TEMPORAL_SCOPE_REQUIRES_CALLER_DATE_REVIEW"
  ],
  "errors": [],
  "skipped_subqueries": [],
  "provenance": [
    {
      "occurrences": [
        {
          "subquery_index": 0,
          "response_index": 0,
          "query": "người lao động ký hợp đồng lao động xác định thời hạn đơn phương chấm dứt hợp đồng phải báo trước bao lâu; tình huống người dùng: Tôi ký hợp đồng lao động thời hạn 24 tháng; đã làm việc được 6 tháng; nay muốn nghỉ việc để chuyển sang công ty khác",
          "request_id": "6770eeb1-92d5-4cb8-b827-16f48824656f",
          "rank": 1,
          "raw_score": 41.1625445045701,
          "score_kind": "BM25",
          "issue_indices": [
            0
          ]
        },
        {
          "subquery_index": 1,
          "response_index": 1,
          "query": "người lao động đơn phương chấm dứt hợp đồng lao động trái pháp luật phải bồi thường những khoản gì; tình huống người dùng: Tôi ký hợp đồng lao động thời hạn 24 tháng; đã làm việc được 6 tháng; nay muốn nghỉ việc để chuyển sang công ty khác",
          "request_id": "8da62a04-9455-4966-8b20-817e023ad077",
          "rank": 1,
          "raw_score": 38.5842878381402,
          "score_kind": "BM25",
          "issue_indices": [
            1
          ]
        }
      ],
      "chunk_id": "01fcd190-2fc8-48ee-8cf5-de8fc77fada7"
    },
    {
      "occurrences": [
        {
          "subquery_index": 0,
          "response_index": 0,
          "query": "người lao động ký hợp đồng lao động xác định thời hạn đơn phương chấm dứt hợp đồng phải báo trước bao lâu; tình huống người dùng: Tôi ký hợp đồng lao động thời hạn 24 tháng; đã làm việc được 6 tháng; nay muốn nghỉ việc để chuyển sang công ty khác",
          "request_id": "6770eeb1-92d5-4cb8-b827-16f48824656f",
          "rank": 2,
          "raw_score": 39.1581494722179,
          "score_kind": "BM25",
          "issue_indices": [
            0
          ]
        },
        {
          "subquery_index": 1,
          "response_index": 1,
          "query": "người lao động đơn phương chấm dứt hợp đồng lao động trái pháp luật phải bồi thường những khoản gì; tình huống người dùng: Tôi ký hợp đồng lao động thời hạn 24 tháng; đã làm việc được 6 tháng; nay muốn nghỉ việc để chuyển sang công ty khác",
          "request_id": "8da62a04-9455-4966-8b20-817e023ad077",
          "rank": 3,
          "raw_score": 35.6693200513719,
          "score_kind": "BM25",
          "issue_indices": [
            1
          ]
        }
      ],
      "chunk_id": "30142e55-42ce-494a-a6fe-a8a10eb46922"
    },
    {
      "occurrences": [
        {
          "subquery_index": 0,
          "response_index": 0,
          "query": "người lao động ký hợp đồng lao động xác định thời hạn đơn phương chấm dứt hợp đồng phải báo trước bao lâu; tình huống người dùng: Tôi ký hợp đồng lao động thời hạn 24 tháng; đã làm việc được 6 tháng; nay muốn nghỉ việc để chuyển sang công ty khác",
          "request_id": "6770eeb1-92d5-4cb8-b827-16f48824656f",
          "rank": 3,
          "raw_score": 36.0295300011835,
          "score_kind": "BM25",
          "issue_indices": [
            0
          ]
        },
        {
          "subquery_index": 1,
          "response_index": 1,
          "query": "người lao động đơn phương chấm dứt hợp đồng lao động trái pháp luật phải bồi thường những khoản gì; tình huống người dùng: Tôi ký hợp đồng lao động thời hạn 24 tháng; đã làm việc được 6 tháng; nay muốn nghỉ việc để chuyển sang công ty khác",
          "request_id": "8da62a04-9455-4966-8b20-817e023ad077",
          "rank": 2,
          "raw_score": 35.9311858285454,
          "score_kind": "BM25",
          "issue_indices": [
            1
          ]
        }
      ],
      "chunk_id": "b6c170cb-de6d-42df-a79b-479251439db6"
    },
    {
      "occurrences": [
        {
          "subquery_index": 0,
          "response_index": 0,
          "query": "người lao động ký hợp đồng lao động xác định thời hạn đơn phương chấm dứt hợp đồng phải báo trước bao lâu; tình huống người dùng: Tôi ký hợp đồng lao động thời hạn 24 tháng; đã làm việc được 6 tháng; nay muốn nghỉ việc để chuyển sang công ty khác",
          "request_id": "6770eeb1-92d5-4cb8-b827-16f48824656f",
          "rank": 4,
          "raw_score": 33.40624818458,
          "score_kind": "BM25",
          "issue_indices": [
            0
          ]
        }
      ],
      "chunk_id": "758fd1e3-72be-44e5-b4de-a55bd2b26a15"
    },
    {
      "occurrences": [
        {
          "subquery_index": 0,
          "response_index": 0,
          "query": "người lao động ký hợp đồng lao động xác định thời hạn đơn phương chấm dứt hợp đồng phải báo trước bao lâu; tình huống người dùng: Tôi ký hợp đồng lao động thời hạn 24 tháng; đã làm việc được 6 tháng; nay muốn nghỉ việc để chuyển sang công ty khác",
          "request_id": "6770eeb1-92d5-4cb8-b827-16f48824656f",
          "rank": 5,
          "raw_score": 33.2157666238166,
          "score_kind": "BM25",
          "issue_indices": [
            0
          ]
        },
        {
          "subquery_index": 1,
          "response_index": 1,
          "query": "người lao động đơn phương chấm dứt hợp đồng lao động trái pháp luật phải bồi thường những khoản gì; tình huống người dùng: Tôi ký hợp đồng lao động thời hạn 24 tháng; đã làm việc được 6 tháng; nay muốn nghỉ việc để chuyển sang công ty khác",
          "request_id": "8da62a04-9455-4966-8b20-817e023ad077",
          "rank": 5,
          "raw_score": 32.326739494673,
          "score_kind": "BM25",
          "issue_indices": [
            1
          ]
        }
      ],
      "chunk_id": "2973a693-2276-4e4f-a233-f7038e4717e0"
    },
    {
      "occurrences": [
        {
          "subquery_index": 1,
          "response_index": 1,
          "query": "người lao động đơn phương chấm dứt hợp đồng lao động trái pháp luật phải bồi thường những khoản gì; tình huống người dùng: Tôi ký hợp đồng lao động thời hạn 24 tháng; đã làm việc được 6 tháng; nay muốn nghỉ việc để chuyển sang công ty khác",
          "request_id": "8da62a04-9455-4966-8b20-817e023ad077",
          "rank": 4,
          "raw_score": 32.612903668669,
          "score_kind": "BM25",
          "issue_indices": [
            1
          ]
        }
      ],
      "chunk_id": "d7f358eb-2586-42c5-9c7d-d2b9f228ca91"
    }
  ]
}
```

## Giới hạn diễn giải

Nguồn dẫn chiếu hoặc mẫu hợp đồng không tự xác nhận chính văn quy định chung. Hash khớp chỉ xác nhận nội dung lưu. Không có nhãn chuyên gia; chưa khẳng định relevance, đủ chứng cứ hoặc hiệu lực áp dụng. Không có mock/fallback deterministic thay cho lỗi LLM.

## Nhận xét kỹ thuật sơ bộ

Các kết quả gồm nghị quyết hỗ trợ/thu hút nhân lực địa phương và văn bản về đào tạo, không nên coi là chính văn quy định chung về nghỉ việc. Đây là nhận xét sơ bộ về phạm vi nguồn, không phải chấm relevance chuyên gia. Cần kiểm tra nội dung từng rank và đúng identity điều luật trước khi dùng để trả lời.
