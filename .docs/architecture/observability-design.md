# Observability Design

> Observability is for debugging, performance/cost control and evaluation. It must not become an uncontrolled store of user or legal-case content.

## 1. Goals

The AI Service should make it possible to answer:
- Which request and workflow failed?
- Which node/agent was running, and how long did it take?
- Which model/provider was actually used, including fallback attempts?
- How many searches and model calls occurred?
- What token usage and cost are known or estimated?
- Why did the workflow stop?
- Which workflow, prompt, model configuration and evaluation dataset versions produced a result?

## 2. Correlation and event model

Use a correlation/request ID across the Backend–AI boundary. Propagate it to workflow runs, node spans, retrieval calls and model-call attempts.

Recommended event categories:
- `request_started` / `request_completed`.
- `workflow_started` / `workflow_completed`.
- `node_started` / `node_completed` / `node_failed`.
- `retrieval_completed` / `retrieval_failed`.
- `model_call_started` / `model_call_completed` / `model_call_failed`.
- `verification_completed` / `verification_failed`.
- `fallback_triggered`.
- `budget_exhausted` / `workflow_terminated`.

Event names are suggestions; keep the implemented schema consistent and documented.

## 3. Minimum fields

| Area | Fields |
|---|---|
| Correlation | `request_id`, trace/run ID, parent span where available |
| Time | UTC timestamp, duration/latency |
| Workflow | workflow name/version, node/agent name, status, `stop_reason` |
| Model | logical profile, actual provider/model, attempt number, fallback flag |
| Usage | input/output tokens; cached/reasoning tokens if reported; cost and cost provenance if available |
| Retrieval | query/round number, result count, error category; safe corpus/index version if available |
| Verification | claim/citation counts, status counts, unresolved issues |
| Reproducibility | prompt version, model configuration version, graph version, evaluation dataset/version |
| Failure | normalized error category, retryable flag, final failure/termination state |

Use explicit `unknown`/null for unavailable usage; do not infer token counts or cost without labeling it as an estimate.

## 4. Logging and privacy rules

Never log:
- API keys, provider secrets, access/refresh tokens or authorization headers.
- Passwords or authentication payloads.
- Full sensitive user prompts, conversation history or uploaded content by default.
- Raw provider responses containing secrets or sensitive content.

Prefer metadata and identifiers over full content. If capturing prompt/response/evidence snapshots is necessary for debugging or evaluation, require an explicit policy defining purpose, access, retention and redaction. Treat legal scenarios and user-provided facts as potentially sensitive.

Logs and telemetry must not be used as an implicit training dataset. Any separate use for evaluation must be explicitly governed and must not assume that real user conversations may be used for model training.

## 5. Metrics

Useful initial metrics:
- Request count and success/error rate.
- End-to-end latency and per-node latency.
- Model calls per request and search/repair rounds per workflow.
- Provider error rate, timeout rate and fallback rate.
- Invalid structured-output rate.
- Retrieval error/empty-result rate.
- Verification status counts and unresolved-claim rate.
- Token usage and cost per request/workflow/model profile.
- Budget-exhaustion and early-termination rates.

Metrics should be segmented by workflow, model profile and configuration version when useful. Avoid high-cardinality labels containing user input or sensitive identifiers.

## 6. Tracing and tooling

Keep the application-facing telemetry interface independent from a specific observability vendor. A local structured logger is sufficient for the first bootstrap; tracing/metrics exporters can be added when the implementation needs them. Do not make an external observability service a mandatory dependency for unit tests.

The selected tool and deployment configuration should be recorded in an ADR/configuration documentation. Provider-specific model-call metadata should be normalized before it reaches the generic telemetry layer.

## 7. Operational failure handling

- A workflow failure must record a normalized error and termination reason.
- A retry should be visible as a separate attempt, not silently overwrite the failed attempt.
- Fallback should record both the triggering failure and the actual provider/model used afterward.
- A partial citation/claim failure must remain visible even if other claims passed.
- Do not emit a generic `success` event if the final answer is incomplete or verification remains unresolved; use an outcome/status that preserves this distinction.
