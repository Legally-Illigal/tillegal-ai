# Debugging

## Principles

Debug the earliest failing boundary, preserve correlation IDs, and prefer reproducible evidence over guessing. Do not make failures disappear by weakening citation verification, disabling validation, or increasing retries without bounds.

## First-response checklist

1. Capture request/run ID, timestamp, environment, and high-level failure category.
2. Locate the boundary: API, orchestration, agent, retrieval, Model Gateway, provider, verification, or persistence.
3. Inspect relevant structured logs and metrics.
4. Check active configuration and workflow/prompt versions without exposing secret values.
5. Reproduce with deterministic fixtures or mocks where possible.
6. Change one variable at a time and run the smallest relevant test.

Never paste API keys, authorization headers, confidential prompts, or raw legal documents into logs or issue trackers.

## Common failure categories

### Startup failure

Check required environment variables, Python/dependency alignment, import cycles, configuration validation, and external services explicitly required by the current implementation. Separate required configuration from optional provider credentials so offline tests remain usable.

### Model Gateway/provider failure

Check provider/model profile mapping, credentials without printing them, network/provider status, request schema, unsupported parameters, timeout, rate limit, quota, and error category. Determine whether multiple layers are retrying the same call. Record provider/model, latency, status category, and retry/fallback events when available. Do not assume every provider error is transient.

### Malformed model output

Check prompt version, expected schema, structured-output configuration, parser errors, truncation/token limits, and assumptions that the model always follows instructions. Treat invalid output as an explicit failure or controlled recovery path; do not coerce it silently into a successful legal answer.

### Retrieval returns no useful evidence

Check query normalization, filters, corpus/index availability, metadata, embedding/index compatibility if vector retrieval is used, ranking parameters, and whether the expected source exists and is current. Distinguish no results, irrelevant results, unavailable source, and source not indexed. Do not invent evidence.

### Citation verification fails

Check source resolution, whether the cited passage supports the claim, preservation of document/article/version/effective-date metadata, and source status when reliable status data exists. If verification cannot be completed, do not label the citation verified.

### Workflow loops or stops unexpectedly

Inspect current node/state, routing conditions, state updates, step/retry budget, stop reason, overwritten evidence, lost identifiers, and exceptions routed back into the same node. Reproduce with fixed node outputs and add assertions for transitions and termination.

### Slow responses or high cost

Break down latency by node and external call. Inspect duplicate retrieval/model calls, oversized context, provider latency, retries/fallback frequency, reflection/evaluation overhead, and concurrency limits. Do not optimize by removing required legal verification; remove redundant work and measure quality impact.

### Missing or inconsistent metrics

Check whether the provider returns usage/cost, whether the gateway normalizes it, and whether the event is persisted/exported. Distinguish zero from not reported. Label estimates as estimates and identify their pricing/configuration basis.

## Safe techniques

- Use mocked model outputs to isolate orchestration behavior.
- Reproduce retrieval problems with approved, sanitized fixtures.
- Enable narrowly scoped debug logging rather than logging all prompt/document content.
- Preserve the failing configuration and record changes made during diagnosis.
- Add a regression test before closing the issue.

## Incident template

```text
Summary:
Environment:
Timestamp:
Request/run ID:
Workflow/prompt version:
Observed behavior:
Expected behavior:
Failure boundary:
Relevant sanitized logs:
Reproduction steps:
Root cause:
Fix:
Regression test:
Remaining risks:
```

## Escalate when

Escalate if the issue may expose secrets/user data, produces incorrect legal citations, bypasses required verification, causes unbounded model calls, or threatens stored-evidence integrity. Preserve sanitized diagnostics and avoid modifying production data during investigation.
