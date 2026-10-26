# Monitoring

## 1. Purpose

Define the minimum operational signals needed to understand the AI Service's health, workflow execution, model-provider behavior, and answer quality.

Monitoring must support troubleshooting without exposing secrets or unnecessarily collecting user content.

## 2. Service-Level Signals

Capture where applicable:

- request count and outcome;
- error rate by safe error category;
- request duration and timeout count;
- active requests and concurrency saturation;
- process health and restart events;
- dependency health;
- request cancellation and overload events.

## 3. Model Gateway Signals

For model calls, record:

- provider and model profile;
- call outcome and duration;
- timeout, rate-limit, and provider-error categories;
- retry and fallback events;
- input/output token counts when provided;
- cost when supplied or reliably calculated from known pricing metadata.

Do not fabricate token or cost values when they are unavailable.

## 4. Workflow Signals

Record the following where relevant:

- workflow name and version;
- workflow run ID and request correlation ID;
- node name, duration, and outcome;
- retrieval result count and safe evidence identifiers;
- verification state;
- retry/fallback count;
- stop reason, cancellation, or workflow-limit exhaustion.

These signals should help reconstruct the processing path of a request without requiring full prompt or document content in logs.

## 5. Evaluation and Quality Signals

Evaluation runs should identify:

- evaluation run ID;
- dataset and rubric versions;
- model profile and prompt versions;
- workflow and retrieval configuration versions;
- per-case results and failure categories;
- aggregate results and known limitations.

For Tillegal, legal-basis correctness and citation verification are priority quality concerns. A fluent answer or a positive self-reflection result is not proof of legal correctness.

## 6. Correlation and Structured Events

Propagate a request/correlation ID across the API, orchestrator, workflow nodes, model gateway, retrieval, and verification components.

A structured event should include applicable fields such as:

- timestamp;
- severity and event name;
- request ID and workflow run ID;
- component, operation, and node;
- duration and outcome;
- provider/model profile;
- retry/fallback count;
- safe error category.

## 7. Privacy and Security

Do not log:
- API keys or credentials;
- authorization headers;
- secret values;
- unrestricted user documents;
- full prompts and answers by default.

If content capture is needed for controlled debugging or evaluation, make it explicit, access-controlled, minimized, appropriately redacted, and subject to a defined retention policy.

## 8. Alerts and Dashboards

Potential alert conditions include:

- sustained increase in API errors or timeouts;
- service readiness failure;
- repeated model-provider failures or rate limits;
- unexpected fallback or retry increases;
- concurrency saturation;
- unexpected token usage or cost;
- regression in release evaluation results.

Thresholds must be set from observed baselines and agreed operational requirements; this document does not invent numeric thresholds.

Recommended dashboard areas:

1. Service reliability.
2. Model Gateway reliability and latency.
3. Workflow outcomes and verification states.
4. Evaluation results and quality trends.
5. Usage and cost, where reliable data exists.

## 9. Related Documents

- `../architecture/observability-design.md`
- `../architecture/evaluation-design.md`
- `../decisions/ADR-004-observability.md`
