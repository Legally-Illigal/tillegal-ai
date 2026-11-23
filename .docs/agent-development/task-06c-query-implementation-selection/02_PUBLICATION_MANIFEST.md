# Publication manifest: chỉ publish bản A

Đây là kế hoạch, chưa thực hiện transfer, worktree, stage, commit, push hoặc PR. Chọn A không đồng nghĩa xóa B. Giữ nguyên WIP trong checkout dùng để publication Retrieval trước đây.

## Đích an toàn

- Source: `D:/DOWNLOAD/tillegal-ai/tillegal-ai-main`.
- Git object store có main hiện tại: `D:/DOWNLOAD/tillegal-ai/retrieval-publish`.
- Official main đã xác minh: `1158a6a40e85395bb91bed90f0d7b1967bbf8deb`.
- Worktree mới đề xuất: `D:/DOWNLOAD/tillegal-ai/query-search-publish`.
- Feature branch mới đề xuất: `codex/query-search-prototype`.

Không publish từ dirty working tree B, không đổi branch B và không tự stash/reset/clean WIP. Tạo worktree mới từ official main để nhận committed stubs, không mang ba file WIP hoặc hai untracked B tests vào branch mới. Main đã có RetrievalService và framework; không cần copy chúng từ export.

## Explicit transfer list

**12 files: 5 modified, 7 added; gồm 6 runtime, 4 tests, 2 tài liệu.** M/A là so với main đã audit, không phải trạng thái WIP B. SHA trong table là prefix của raw source SHA-256; [manifest JSON](evidence/publication-manifest.json) có full raw và LF-normalized SHA-256. Git core.autocrlf=true có thể làm blob EOL khác raw filesystem, nên phân biệt hai fingerprints.

| Change | Path tương đối | Source SHA-256 prefix |
|---|---|---|
| M | `src/applications/tillegal/agents/query/agent.py` | `b196d7c02e3b` |
| M | `src/applications/tillegal/agents/search/agent.py` | `d00506511093` |
| A | `src/query_search_bootstrap.py` | `122c80bbaabe` |
| M | `src/retrieval_bootstrap.py` | `e5ef67702fc7` |
| M | `src/applications/tillegal/graphs/legal_qa.py` | `9ee6208297ec` |
| M | `src/applications/tillegal/state/legal_qa_state.py` | `641837c50d6a` |
| A | `tests/unit/applications/tillegal/test_query_hardening.py` | `d1a7b6f20092` |
| A | `tests/unit/applications/tillegal/test_query_search.py` | `c2e5c76cd526` |
| A | `tests/unit/applications/tillegal/test_query_search_multimode.py` | `6f388f05434f` |
| A | `tests/graph/test_query_search_workflow.py` | `1d570e28a78a` |
| A | `.docs/agent-development/task-03-query-search-retrieval/02_INPUT_OUTPUT_CONTRACTS.md` | `dbf2caebdca9` |
| A | `.docs/agent-development/task-05-langgraph-integration/10_FINAL_QUERY_SEARCH_HANDOFF.md` | `dafa9771905b` |

Hunk bắt buộc ở src/retrieval_bootstrap.py22–70: thêm keyword-only timeout_seconds:float=30 và forward vào RetrievalService constructor. Thiếu hunk này, create_query_search24–42 sẽ truyền keyword không được factory cũ nhận. Không thay retrieval algorithm, embeddings, SQL hoặc indexes.

Hai docs là tài liệu lịch sử độc lập không có links tới files chưa chuyển. Không biến số liệu Task 5 trong docs thành kết quả publication worktree mới. Không copy toàn source export hoặc toàn bộ agent-development directory.

## WIP B phải loại khỏi PR và giữ nguyên tại chỗ

Các paths dưới đây tương đối với `D:/DOWNLOAD/tillegal-ai/retrieval-publish`:

| Path | Disposition |
|---|---|
|src/applications/tillegal/agents/query/__init__.py |Không chuyển bản WIP export QueryAgent/QueryAgentInput |
|src/applications/tillegal/agents/query/agent.py |Không lấy nội dung B; path cùng tên trong PR phải lấy từ A |
|src/applications/tillegal/agents/query/schemas.py |Không lấy 239 dòng schema B; giữ committed stub ở worktree mới |
|tests/unit/applications/tillegal/agents/query/test_agent.py |Giữ untracked B test, không chuyển |
|tests/unit/applications/tillegal/agents/query/test_contracts.py |Giữ untracked B test, không chuyển |
|.docs/development/query-search-design/00_repository_audit.md |Không đưa design WIP vào PR implementation A |
|.docs/development/query-search-design/01_system_architecture.md |Cùng disposition |
|.docs/development/query-search-design/02_query_agent_design.md |Cùng disposition |
|.docs/development/query-search-design/03_search_agent_design.md |Cùng disposition |
|.docs/development/query-search-design/04_contracts_and_state.md |Cùng disposition |
|.docs/development/query-search-design/05_testing_and_evaluation.md |Cùng disposition |
|.docs/development/query-search-design/06_implementation_roadmap.md |Cùng disposition |
|.docs/development/query-search-design/07_architecture_decisions.md |Cùng disposition |
|.docs/development/query-search-design/08_open_questions_and_blockers.md |Cùng disposition |
|.docs/development/query-search-design/README.md |Cùng disposition |

Không copy A query/__init__.py hoặc schemas.py để “dọn” B: hai files committed trên main là stubs phù hợp với current A imports. Fresh worktree giữ chúng nguyên trạng, không cần động đến WIP B.

Ngoài manifest: không chuyển ai_core, legacy pilot, .env, model weights, .venv/caches, generated outputs, bulk diagnostics, root README/.gitignore cũ, pyproject.toml/uv.lock/configs hoặc các formatting-only differences. Main có ignore rules bảo vệ model/secrets tốt hơn export. Dependencies và public Retrieval contracts đã tương thích; chỉ Query/Search/state/graph stubs được hoàn thiện.

## Các bước thực hiện sau khi được phép

1. Đọc lại remote main bằng ls-remote. Nếu SHA thay đổi, dừng để audit lại; không tự fetch/merge/rebase.
2. Xác nhận path worktree/branch đề xuất chưa tồn tại. Tạo clean worktree từ đúng main SHA, không từ dirty B files hoặc retrieval feature HEAD.

```powershell
git -C 'D:\DOWNLOAD\tillegal-ai\retrieval-publish' worktree add `
  -b codex/query-search-prototype `
  'D:\DOWNLOAD\tillegal-ai\query-search-publish' `
  1158a6a40e85395bb91bed90f0d7b1967bbf8deb
```

3. Kiểm worktree mới clean và HEAD đúng base. Đọc manifest JSON; kiểm raw SHA từng source path rồi copy đúng 12 paths, tạo parent directories cần thiết. Không recursive directory copy; không tự thêm files ngoài manifest.
4. CWD là worktree mới. Dùng Python environment hiện có nhưng không copy environment. Ruff check và format --check trên 10 Python files trong manifest, không dùng --fix. Chạy A regression command trong [test-results.json](evidence/test-results.json), thay JUnit output thành approved audit/temp path riêng. Lượt audit hiện tại A320 pass, publication worktree chưa được tạo/test.
5. Kiểm graph30 cases trong suite, all-mode actual service/fake ports, date/policy mapping, clarification stop, native subtype/JSON, failed-prefix, timeout/cancel/isolation. Không cần live Supabase để chốt contract này; không đổi thành production-quality claim.
6. Review git status, git diff --check, tracked diff và new files. Xác nhận không sửa pyproject/lock/retrieval algorithms/framework/migrations; không có B tests/schema exports. Rà secrets và staged sizes; chỉ dùng values trong process, không in token. So sánh LF-normalized content khi EOL khác.
7. Stage bằng explicit 12 paths; không git add . Kiểm git diff --cached --name-status, --check và full staged diff; staged set phải đúng manifest.
8. Chỉ sau tests/review đạt, commit vào feature branch, push branch và mở PR vào main. Không push trực tiếp main.

Suggested commit: `feat(agents): integrate deterministic query/search with retrieval and LangGraph`.

PR title: `Integrate deterministic Query/Search with RetrievalService and LangGraph`.

PR body: Query tạo six-field plan; Search dùng trusted options và tuần tự gọi existing RetrievalService, giữ native responses và dừng ở classified failure; LangGraph dừng clarification hoặc tạo validated JudgeHandoff v1. Không Judge/Answer/HTTP/DB changes. Ghi kết quả lint/tests thật trên publication worktree trước khi mở PR; 320 pass của export là reference riêng.

## Remaining risks và stop

A vẫn có heuristic intent/domain/ambiguity, temporal mentions chưa reconcile tự động với trusted date, tab-only clauses có thể fail receiving Request, không cross-query fusion/dedup, không legal sufficiency. Shared-resource lifecycle/ACL/load vàlive graph Dense/Hybrid/rerank chưa được chứng minh chỉ bởi offline suite. Đây là prototype limits đã ghi, chưa có lý do phải thaycontract bằng B trước publication.

Chưa chạy bất kỳ bước Git write/transfer nào ở trên. Không xóa B, không merge implementations, không tạo PR. Chốt A; implementation/publication là task riêng sau quyết định của người dùng.
