# Observability Skill
---
name: observability
description: Implement structured logging, tracing, metrics, and operational diagnostics for Tillegal AI Service.
---

## Purpose

Make AI Service behavior diagnosable across API requests, graph execution, agent nodes, and model calls without unnecessarily exposing sensitive information.

Follow the approved observability architecture and existing instrumentation libraries.

## When to Use

- Adding logs, metrics, or traces.
- Instrumenting LangGraph workflows.
- Recording model-call duration and usage.
- Investigating failures or latency.
- Improving operational monitoring.
- Adding evaluation-run metadata.

## Procedure

### Step 1: Identify the Execution Path

Determine which components need visibility.

Where applicable, trace the execution path across:

- Incoming request or workflow invocation.
- Graph execution.
- Individual node execution.
- Model Gateway invocation.
- Provider response.
- Validation and evaluation.
- Final outcome.

Do not introduce distributed tracing for a single local function unless it serves a clear purpose.

### Step 2: Define Correlation

Use the project's established request and execution identifiers.

Where supported, associate events with:

- Request or correlation ID.
- Workflow execution ID.
- Node or component name.
- Model-call ID.
- Evaluation-run ID.
- Code, prompt, or configuration version where relevant.

Avoid using personal information or raw user queries as correlation identifiers.

### Step 3: Add Structured Logging

Record meaningful events such as initialization, execution start, completion, retry, fallback, and failure.

Include relevant structured fields, for example:

- Timestamp.
- Component and operation.
- Outcome or error category.
- Duration.
- Retry attempt.
- Correlation identifiers.

Follow the project's logging conventions and avoid ad hoc output.

### Step 4: Add Metrics

Use metrics that help explain operational behavior, such as:

- Request and workflow counts.
- Success and failure rates.
- Model-call latency.
- Workflow duration.
- Timeout and retry counts.
- Provider error categories.
- Token usage when available.
- Cost when reliably available.
- Evaluation metrics where applicable.

Define metric units and aggregation semantics. Avoid high-cardinality labels containing user IDs, raw prompts, document content, or arbitrary exception text.

### Step 5: Instrument Model Calls

Capture relevant metadata at the Model Gateway boundary.

Distinguish:

- Requested model from resolved model where available.
- Reported token usage from unavailable usage.
- Reported cost from estimated cost.
- Model-call duration from total workflow duration.
- Provider failure from application-level validation failure.

Do not invent metadata or imply that a model call succeeded when it failed.

### Step 6: Instrument Workflow Failures

Record sufficient context to identify the failing component and failure category.

Where appropriate, distinguish:

- Invalid input.
- Graph routing or state error.
- Model-provider failure.
- Structured-output validation failure.
- Retrieval failure.
- Retry exhaustion.
- Cancellation or timeout.
- Unexpected internal exception.

Preserve sanitized exception context without exposing credentials or sensitive content.

### Step 7: Validate Instrumentation

Test that:

- Successful executions emit expected events.
- Failures remain diagnosable.
- Correlation IDs propagate where supported.
- Metrics use consistent units and labels.
- Instrumentation does not change functional behavior.
- Sensitive information is not unintentionally recorded.

## Privacy and Security

Do not log full prompts, model responses, uploaded documents, legal case narratives, API keys, or authorization headers by default.

Any content capture for debugging or evaluation must follow an approved data-handling policy with appropriate access controls, retention, and redaction.

## Guardrails

- Do not introduce an observability backend without a justified requirement.
- Do not make high-cardinality metrics from arbitrary user content.
- Do not silently swallow instrumentation errors if doing so hides a critical operational problem.
- Do not allow nonessential telemetry failures to destabilize core execution unless the approved design requires otherwise.
- Do not claim monitoring or alerting exists merely because metrics are emitted.

## Expected Output

Instrumented execution paths, defined event and metric semantics, relevant tests, and documentation describing available signals and limitations.

## Completion Checklist

- [ ] Important execution boundaries are observable.
- [ ] Correlation is preserved where supported.
- [ ] Latency and usage values have clear semantics.
- [ ] Failures can be diagnosed without exposing sensitive content.
- [ ] Metric labels avoid unnecessary high cardinality.
- [ ] Instrumentation has been validated.
