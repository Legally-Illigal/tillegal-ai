# Model Gateway

> Shared interface for model calls. This document describes the intended contract and policies, not a commitment to every optional capability of every provider.

## 1. Purpose

All workflow nodes should call a common LLM Gateway rather than directly depending on provider SDKs. Provider adapters normalize request/response shapes, usage metadata and errors so that model/provider changes do not require rewriting application agents.

The current target implementation is **LiteLLM behind the shared gateway**. Keep LiteLLM-specific details inside the adapter. ADR-002 records this proposal; provider/model selection and fallback still require testing before the decision is accepted.

## 2. Responsibilities

The gateway should:
- Resolve a logical model/profile from configuration.
- Apply model parameters and task-level policy.
- Support structured output/schema constraints when available.
- Apply timeout and bounded retry policy.
- Perform fallback only when explicitly configured and when the error is eligible.
- Normalize response text/structured data, finish status, provider/model identity, token usage and cost metadata when available.
- Emit telemetry for each attempt, including failures.
- Redact credentials and avoid logging sensitive request content by default.

The gateway does not decide whether a legal conclusion is correct. That remains the responsibility of workflow policies, evidence checks and verification.

## 3. Suggested logical contract

A call should carry a typed request conceptually containing:
- `request_id` / trace context.
- `task_name` or logical use case.
- `model_profile` (logical name, not a hard-coded provider in the agent).
- Messages/prompt inputs and optional structured-output schema.
- Task-level generation settings.
- Timeout and usage budget.
- Data-handling/logging policy.

The normalized result should contain:
- Text and/or validated structured payload.
- Provider and model actually used.
- Finish/status information.
- Input/output token counts and cached/reasoning token counts only when reported by provider.
- Cost estimate/value and its provenance when available.
- Latency and attempt count.
- Structured error/fallback information.
- Provider request ID when safe/useful for diagnostics.

Do not fabricate missing token/cost fields. Represent unavailable usage as unknown/null and distinguish reported values from estimates.

## 4. Configuration and profiles

Use configuration rather than model names scattered across agent code. A logical profile may specify:
- Primary provider/model.
- Optional fallback sequence.
- Supported capabilities (structured output, tool calling, streaming, etc.) where needed.
- Default parameters and task-specific overrides.
- Timeout, retry and fallback policy.
- Cost/usage limits.
- Data-handling policy.

Do not assume all models support the same parameter names or reasoning controls. Normalize common settings where possible, and validate or omit provider-specific settings when unsupported. Do not expose provider-specific “thinking” or reasoning parameters as if they were universally portable.

Secrets must come from environment variables or an approved secret source; never commit real keys or include them in prompts/logs.

## 5. Failure and fallback policy

1. Set a timeout for every remote model call.
2. Retry only eligible transient errors and cap attempts.
3. Do not retry non-retryable errors indefinitely (for example invalid credentials or invalid request configuration).
4. Fallback is permitted only when configured and when the failure category allows it.
5. Validate fallback output using the same schemas and verification steps as primary output.
6. Record the provider/model actually used, attempt sequence, error category and final outcome.
7. If no usable provider remains, return a structured unavailable/error result rather than an unverified legal answer.

A successful provider response can still be unusable because of invalid schema or unsupported claims; transport success is not application success.

## 6. Observability contract

At minimum, record per model-call attempt:
- Timestamp and duration.
- Request/correlation ID and workflow/node/task name.
- Configured profile and actual provider/model.
- Success/failure and normalized error category.
- Attempt number and fallback status.
- Input/output token usage and other token categories when provider reports them.
- Cost and whether it is provider-reported or estimated, when available.
- Prompt/model configuration version identifiers.
- Optional safe provider request ID.

Do not log API keys, auth tokens or sensitive prompt content by default. If prompt/response capture is needed for evaluation, make it explicit, access-controlled and governed by a separate data policy.

## 7. Testing

- Unit-test gateway policy with a fake adapter.
- Contract-test normalization for each provider adapter.
- Test timeout, retry eligibility, fallback order, malformed output and missing usage metadata.
- Test that fallback does not skip application validation or legal verification.
- Keep ordinary unit tests independent of live provider credentials.
