# Chạy các module TilLegal đã tích hợp

Từ thư mục repo chính, dùng Python 3.12 và các dependency trong lockfile.

```powershell
uv sync --locked --group dev
uv run python -m pytest tests/transferred -q
uv run python -m pytest -q
```

Kiểm thử dùng văn bản giả định, fake encoder và fixture LLM. Test nguồn nằm trong `tests/transferred/test_module_flow.py`. Đường chạy thực tế nhận một Supabase client của server, snapshot E5 trên máy và hai provider đã cấu hình. Review migration `20261106180000_staging_version_windows.sql` trên DB thử nghiệm trước khi sử dụng. Cần đủ các migration trước đó và role Supabase. Đặt `SUPABASE_AUTO_MIGRATE=false` khi chỉ kiểm tra import/bootstrap.

Cài backend local khi cần inference thật. Các phiên bản của torch/transformers trong requirements lấy từ môi trường repo nguồn. Khả năng cung cấp wheel còn phụ thuộc hệ điều hành và phiên bản Python.

```powershell
uv pip install -r requirements-rag-local.txt
```

Ví dụ khởi tạo trong tiến trình server, với `client` là Supabase client đã cấu hình. Đường dẫn model và revision là cấu hình của môi trường. Factory khởi tạo encoder một lần. Lời gọi Gemini thật cần chủ động cho phép gửi nội dung, đặt model và key trong môi trường. Factory cũng nhận provider được inject.

```python
import os
from src.applications.tillegal.composition import create_local_modules
from src.applications.tillegal.agents.response.schemas import LLM_OUTPUT_SCHEMA
from src.integrations.llm.gemini_provider import GeminiProvider

modules = create_local_modules(
    client,
    model_path=os.environ["TILLEGAL_E5_PATH"],
    revision=os.environ["TILLEGAL_E5_REVISION"],
    judge_provider=GeminiProvider.from_environment(allow_live=True),
    summary_provider=GeminiProvider.from_environment(allow_live=True, output_schema=LLM_OUTPUT_SCHEMA),
)
```

Trong hàm async, dùng `record` đúng schema staging hoặc dựng bằng `build_document`. Xem hàm `document()` trong test cho ví dụ HTML hoàn chỉnh.

```python
from src.applications.tillegal.ingestion.data_contracts import DocumentVersion
from src.applications.tillegal.agents.judge.adapter import adapt_evidence_bundle
from src.applications.tillegal.agents.response.adapter import make_summary_input

version_id = await modules.ingestion.ingest(DocumentVersion.from_dict(record))
result = await modules.retrieval.search(question, version_ids=(version_id,),
                                        request_id=request_id, method="hybrid")
bundle = result["evidence_bundle"]
context = dict(question=question, query_plan=query_plan, as_of_date=as_of_date)
evaluation = await modules.evaluate(adapt_evidence_bundle(
    bundle, **context, search_rounds_completed=1, query_history=[]))
draft = await modules.summarize(make_summary_input(bundle, evaluation, **context))
```

`query_plan` cần `issues` với ID và text. Caller cấp câu hỏi, ngày và lịch sử gốc. Truyền `parsed=` cho phiên bản đã có kết quả parser cùng schema. Các mode retrieval là `bm25`, `dense`, `hybrid`. Muốn rerank, inject `LocalReranker` vào factory. Khi khởi tạo web app, `create_app(settings, tillegal_modules=modules)` cung cấp các module qua `app.state.tillegal_modules`. Các lời gọi này độc lập với routing LangGraph.

Đường E5 dùng corpus thực nghiệm với danh sách version rõ ràng. Các phiên bản được hydrate từ DB rồi chấm điểm trong RAM, phù hợp phạm vi corpus nhỏ. Vector được gom bằng max cosine theo chunk. Đường SQL legacy 1536 chiều vẫn có contract và bộ lọc riêng. Không sử dụng kết quả staging để tuyên bố đã kiểm chứng luật.


Kiểm thử SQL tùy chọn dùng PostgreSQL và pgvector nhúng trong RAM, qua Node.js. Lệnh dưới chạy độc lập với URL và credentials Supabase.

```powershell
$env:PGLITE_TEST_PREFIX = Join-Path $env:TEMP 'tillegal-pgvector-test'
npm install --prefix $env:PGLITE_TEST_PREFIX --ignore-scripts @electric-sql/pglite@0.5.15 @electric-sql/pglite-pgvector@0.0.16
uv run python -m pytest -q tests/transferred/test_pgvector.py
```
