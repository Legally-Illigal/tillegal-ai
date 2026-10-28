# tillegal-ai
Tillegal - Phần AI Service của hệ thống, repo nhằm triển khai chi tiết cho hệ thống AI.

The directory tree below is the agreed target structure currently being implemented. It describes the intended architecture; some listed modules may not exist in the working code yet.

## Supabase

The API creates a Supabase client during startup when database credentials are present. Configure these values in a local `.env` file (copy `.env.example`); do not commit real keys:

```dotenv
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<server-only-key>
SUPABASE_VECTOR_TABLE=legal_documents
```

Use the project URL from Supabase Project Settings → API. Keep the service-role key on the server only because it bypasses Row Level Security. If the service-role key is not available, `SUPABASE_ANON_KEY` can be used with appropriate RLS policies. `SUPABASE_URL` and at least one API key must be configured together. Without either value, the API still starts with `app.state.supabase_client` set to `None`, which supports local development without Supabase.

The application initializes the Supabase API client but does not create database tables or policies. Create the required schema and RLS policies in Supabase before using database-backed features.

tillegal-ai-service/
│
├── .agents/                              # AI Coding Harness
│   ├── rules/
│   │   ├── project.md                    # Quy tắc chung của dự án
│   │   ├── architecture.md               # Quy tắc kiến trúc
│   │   ├── python.md                     # Python coding conventions
│   │   ├── testing.md                    # Quy tắc kiểm thử
│   │   ├── security.md                   # Secrets, PII, dữ liệu nhạy cảm
│   │   └── documentation.md              # Quy tắc viết tài liệu
│   │
│   ├── agents/
│   │   ├── architect.md                  # Phân tích kiến trúc
│   │   ├── python-developer.md            # Phát triển Python
│   │   ├── langgraph-engineer.md          # LangGraph và Agent workflow
│   │   ├── llm-engineer.md                # Model gateway, prompt, LLM
│   │   ├── test-engineer.md               # Thiết kế và thực hiện test
│   │   ├── reviewer.md                   # Review code và kiến trúc
│   │   └── documentation-writer.md        # Tài liệu kỹ thuật
│   │
│   ├── skills/
│   │   ├── project-bootstrap/
│   │   │   └── SKILL.md
│   │   ├── python-development/
│   │   │   └── SKILL.md
│   │   ├── langgraph-development/
│   │   │   └── SKILL.md
│   │   ├── litellm-integration/
│   │   │   └── SKILL.md
│   │   ├── prompt-engineering/
│   │   │   └── SKILL.md
│   │   ├── evaluation-design/
│   │   │   └── SKILL.md
│   │   ├── observability/
│   │   │   └── SKILL.md
│   │   ├── testing/
│   │   │   └── SKILL.md
│   │   ├── code-review/
│   │   │   └── SKILL.md
│   │   └── documentation/
│   │       └── SKILL.md
│   │
│   ├── workflows/
│   │   ├── implement-task.md              # Quy trình triển khai task
│   │   ├── investigate-issue.md            # Điều tra lỗi
│   │   ├── review-changes.md               # Review thay đổi
│   │   ├── add-agent.md                    # Thêm Agent mới
│   │   ├── add-model-provider.md            # Tích hợp model/provider
│   │   └── release-checklist.md             # Kiểm tra trước release
│   │
│   └── templates/
│       ├── task.md
│       ├── bug-report.md
│       └── architecture-decision.md
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                         # Lint, type check, test
│   │   ├── security.yml                   # Dependency/security checks
│   │   └── build.yml                      # Build container
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
│
├── .vscode/
│   ├── extensions.json                    # Extension khuyến nghị
│   └── settings.json                      # Cấu hình editor dùng chung
│
├── configs/
│   ├── app.yaml                           # Cấu hình ứng dụng
│   ├── models.yaml                        # Model profiles
│   ├── routing.yaml                       # Routing và fallback policies
│   ├── evaluation.yaml                    # Evaluation policies
│   ├── observability.yaml                 # Logging/tracing settings
│   └── logging.yaml                       # Log format và log levels
│
├── docs/
│   ├── README.md
│   ├── architecture/
│   │   ├── overview.md
│   │   ├── component-design.md
│   │   ├── dependency-rules.md
│   │   ├── runtime-flow.md
│   │   ├── model-gateway.md
│   │   ├── evaluation-design.md
│   │   ├── observability-design.md
│   │   └── diagrams/
│   │
│   ├── development/
│   │   ├── setup.md
│   │   ├── coding-conventions.md
│   │   ├── testing-guide.md
│   │   ├── debugging.md
│   │   └── adding-a-new-agent.md
│   │
│   ├── operations/
│   │   ├── configuration.md
│   │   ├── deployment.md
│   │   ├── monitoring.md
│   │   ├── troubleshooting.md
│   │   └── incident-response.md
│   │
│   ├── decisions/
│   │   ├── ADR-001-langgraph.md
│   │   ├── ADR-002-litellm.md
│   │   ├── ADR-003-evaluation.md
│   │   └── ADR-004-observability.md
│   │
│   └── tasks/
│       ├── backlog/
│       ├── in-progress/
│       ├── completed/
│       └── templates/
│
├── src/
│   ├── __init__.py
│   ├── main.py                        # Application entry point
│   ├── bootstrap.py                   # Khởi tạo dependency và runtime
│   │
│   ├── api/                           # FastAPI presentation layer
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   ├── middleware/
│   │   │   ├── request_context.py
│   │   │   ├── request_logging.py
│   │   │   └── error_handling.py
│   │   ├── routes/
│   │   │   ├── health.py
│   │   │   ├── chat.py
│   │   │   ├── executions.py
│   │   │   └── admin.py
│   │   └── schemas/
│   │       ├── common.py
│   │       ├── chat.py
│   │       └── execution.py
│   │
│   ├── core/                          # Cross-cutting primitives
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── exceptions.py
│   │   ├── result.py
│   │   ├── identifiers.py
│   │   ├── clock.py
│   │   └── security.py
│   │
│   ├── application/                   # Application use cases
│   │   ├── interfaces/
│   │   │   ├── llm_gateway.py
│   │   │   ├── checkpointer.py
│   │   │   ├── trace_store.py
│   │   │   └── evaluation_store.py
│   │   ├── services/
│   │   │   ├── chat_service.py
│   │   │   ├── execution_service.py
│   │   │   └── evaluation_service.py
│   │   └── dto/
│   │       ├── chat.py
│   │       ├── execution.py
│   │       └── evaluation.py
│   │
│   ├── framework/                     # Reusable Multi-Agent Core
│   │   ├── runtime/
│   │   │   ├── executor.py
│   │   │   ├── execution_context.py
│   │   │   ├── lifecycle.py
│   │   │   └── cancellation.py
│   │   │
│   │   ├── agents/
│   │   │   ├── base.py
│   │   │   ├── contracts.py
│   │   │   ├── registry.py
│   │   │   └── metadata.py
│   │   │
│   │   ├── graphs/
│   │   │   ├── factory.py
│   │   │   ├── registry.py
│   │   │   ├── compiler.py
│   │   │   ├── routing.py
│   │   │   ├── policies.py
│   │   │   └── subgraphs.py
│   │   │
│   │   ├── state/
│   │   │   ├── base.py
│   │   │   ├── messages.py
│   │   │   ├── artifacts.py
│   │   │   └── reducers.py
│   │   │
│   │   ├── llm/
│   │   │   ├── gateway.py
│   │   │   ├── registry.py
│   │   │   ├── model_profile.py
│   │   │   ├── capabilities.py
│   │   │   ├── request_options.py
│   │   │   ├── response.py
│   │   │   ├── errors.py
│   │   │   ├── routing/
│   │   │   │   ├── router.py
│   │   │   │   ├── fallback.py
│   │   │   │   ├── retry_policy.py
│   │   │   │   ├── timeout_policy.py
│   │   │   │   └── budget_policy.py
│   │   │   ├── providers/
│   │   │   │   └── litellm_adapter.py
│   │   │   └── telemetry/
│   │   │       ├── usage.py
│   │   │       ├── cost.py
│   │   │       └── callbacks.py
│   │   │
│   │   ├── prompts/
│   │   │   ├── registry.py
│   │   │   ├── template.py
│   │   │   ├── renderer.py
│   │   │   ├── versioning.py
│   │   │   └── context/
│   │   │       ├── builder.py
│   │   │       ├── policies.py
│   │   │       └── token_budget.py
│   │   │
│   │   ├── tools/
│   │   │   ├── registry.py
│   │   │   ├── contracts.py
│   │   │   ├── execution.py
│   │   │   ├── permissions.py
│   │   │   └── error_handling.py
│   │   │
│   │   ├── evaluation/
│   │   │   ├── contracts.py
│   │   │   ├── runner.py
│   │   │   ├── registry.py
│   │   │   ├── result.py
│   │   │   ├── rubrics.py
│   │   │   ├── datasets.py
│   │   │   ├── evaluators/
│   │   │   │   ├── schema.py
│   │   │   │   ├── relevance.py
│   │   │   │   ├── groundedness.py
│   │   │   │   ├── completeness.py
│   │   │   │   └── llm_judge.py
│   │   │   ├── reflection/
│   |   │   │   ├── node.py
│   │   │   │   ├── policies.py
│   │   │   │   └── revision.py
│   │   │   └── reporting/
│   │   │       ├── summary.py
│   │   │       └── metrics.py
│   │   │
│   │   ├── observability/
│   │   │   ├── logging.py
│   │   │   ├── tracing.py
│   │   │   ├── metrics.py
│   │   │   ├── events.py
│   │   │   ├── correlation.py
│   │   │   └── redaction.py
│   │   │
│   │   ├── persistence/
│   │   │   ├── checkpointing.py
│   │   │   ├── stores.py
│   │   │   └── serializers.py
│   │   │
│   │   ├── resilience/
│   │   │   ├── retry.py
│   │   │   ├── circuit_breaker.py
│   │   │   ├── concurrency.py
│   │   │   └── idempotency.py
│   │   │
│   │   └── human_in_the_loop/
│   │       ├── interrupts.py
│   │       ├── approvals.py
│   │       └── resume.py
│   │
│   ├── integrations/                  # External infrastructure adapters
│   │   ├── database/
│   │   │   ├── session.py
│   │   │   ├── models.py
│   │   │   ├── repositories/
│   │   │   └── migrations/
│   │   ├── langgraph/
│   │   │   └── postgres_checkpointer.py
│   │   ├── observability/
│   │   │   ├── langsmith.py
│   │   │   ├── opentelemetry.py
│   │   │   └── exporters.py
│   │   ├── cache/
│   │   │   └── redis_cache.py
│   │   └── secrets/
│   │       └── environment_secrets.py
│   │
│   ├── applications/                  # Application-specific modules
│   │   └── tillegal/
│   │       ├── __init__.py
│   │       ├── agents/
│   │       │   ├── query/
│   │       │   │   ├── agent.py
│   │       │   │   ├── prompts.py
│   │       │   │   └── schemas.py
│   │       │   ├── search/
│   │       │   │   ├── agent.py
│   │       │   │   ├── prompts.py
│   │       │   │   └── schemas.py
│   │       │   ├── judge/
│   │       │   │   ├── agent.py
│   │       │   │   ├── prompts.py
│   │       │   │   └── schemas.py
│   │       │   └── response/
│   │       │       ├── agent.py
│   │       │       └── prompts.py
│   │       ├── graphs/
│   │       │   ├── legal_qa.py
│   │       │   └── citation_verification.py
│   │       ├── state/
│   │       │   └── legal_qa_state.py
│   │       ├── tools/
│   │       │   ├── legal_retrieval.py
│   │       │   └── citation_lookup.py
│   │       ├── retrieval/
│   │       │   ├── retriever.py
│   │       │   ├── reranker.py
│   │       │   └── document_models.py
│   │       ├── evaluation/
│   │       │   ├── legal_grounding.py
│   │       │   ├── citation_accuracy.py
│   │       │   └── legal_answer_quality.py
│   │       └── policies/
│   │           ├── legal_source_policy.py
│   │           └── legal_answer_policy.py
│   │
│   └── workers/                       # Background jobs, if needed
│       ├── tasks.py
│       └── worker.py
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── framework/
│   │   │   ├── test_agent_contracts.py
│   │   │   ├── test_graph_routing.py
│   │   │   ├── test_model_gateway.py
│   │   │   ├── test_fallback.py
│   │   │   ├── test_budget_policy.py
│   │   │   ├── test_prompt_renderer.py
│   │   │   └── test_evaluation.py
│   │   └── applications/
│   │       └── tillegal/
│   │
│   ├── integration/
│   │   ├── test_fastapi.py
│   │   ├── test_database.py
│   │   ├── test_checkpointer.py
│   │   └── test_litellm_adapter.py
│   │
│   ├── graph/
│   │   ├── test_execution_flow.py
│   │   ├── test_retry_and_recovery.py
│   │   ├── test_reflection_loop.py
│   │   └── test_interrupt_resume.py
│   │
│   ├── evaluation/
│   │   ├── test_groundedness.py
│   │   ├── test_quality_regression.py
│   │   └── datasets/
│   │
│   ├── contract/
│   │   ├── test_llm_gateway_contract.py
│   │   └── test_evaluator_contract.py
│   │
│   └── fixtures/
│       ├── llm_responses/
│       ├── documents/
│       └── graphs/
│
├── scripts/
│   ├── dev_setup.py
│   ├── check_environment.py
│   ├── run_evaluation.py
│   ├── export_traces.py
│   └── seed_dev_data.py
│
├── deployments/
│   ├── docker/
│   │   └── Dockerfile
│   ├── compose/
│   │   └── docker-compose.yml
│   └── observability/
│       └── otel-collector.yaml
│
├── .env.example
├── .gitignore
├── .dockerignore
├── .python-version
├── .pre-commit-config.yaml
├── pyproject.toml
├── uv.lock
├── Makefile
├── README.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── LICENSE
└── SECURITY.md