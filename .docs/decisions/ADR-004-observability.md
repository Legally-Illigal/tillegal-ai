# ADR-004: Use Structured, Correlated Observability

- **Status:** Proposed
- **Date:** 2026-10-26
- **Decision owners:** Tillegal AI Service team

## Context

A multi-agent workflow may execute multiple retrieval, model, verification, and fallback steps for a single user request. Unstructured or uncorrelated logs make it difficult to reconstruct execution, identify slow nodes, investigate provider failures, or trace legal-quality incidents.

At the same time, logs may expose prompts, retrieved legal documents, personal information, or credentials if content capture is uncontrolled.

## Decision

Use structured logs and consistent correlation identifiers across the API, orchestrator, workflow nodes, Model Gateway, retrieval, verification, and persistence components.

Keep telemetry backends behind an implementation boundary where practical so that logging, metrics, and tracing implementations can change without requiring widespread changes to business logic.

## Minimum Telemetry

Capture applicable fields:

- timestamp and severity;
- event name and component;
- request/correlation ID and workflow run ID;
- workflow version and node name;
- operation outcome and safe error category;
- operation duration;
- provider and model profile for model calls;
- retry and fallback events;
- token usage and cost when available;
- retrieval and verification states;
- workflow stop reason.

Propagate correlation IDs consistently across component boundaries. Use stable evidence identifiers where possible rather than copying entire document contents into telemetry.

## Privacy and Security Constraints

- Never log API keys, credentials, access tokens, or authorization headers.
- Do not capture complete prompts, answers, or retrieved documents by default.
- Make any controlled payload capture explicit, access-controlled, minimized, and subject to retention rules.
- Redact sensitive values where appropriate.
- Prevent client-facing error responses from exposing internal stack traces or secrets.
- Ensure access to telemetry follows the project's access-control requirements.

## Alternatives Considered

1. **Structured logs with correlated metrics/traces:** supports request reconstruction and backend flexibility.
2. **Ad hoc text logs:** easy to start with but harder to aggregate and correlate.
3. **Vendor-specific instrumentation throughout the application:** may provide rich capabilities but increases coupling.

## Consequences

### Benefits

- Requests can be traced across workflow stages.
- Latency, failures, retries, and fallback behavior become measurable.
- Quality investigations can connect outputs to model, prompt, and workflow versions.
- Operational evidence can be collected without defaulting to unrestricted content logging.

### Trade-offs

- Instrumentation requires implementation and maintenance.
- Correlation identifiers must be propagated correctly.
- Redaction, retention, and telemetry access need ongoing review.

## Validation Before Acceptance

- Trace a request across multiple workflow nodes.
- Verify that provider failures and fallback decisions are observable.
- Confirm unavailable token/cost values remain absent rather than fabricated.
- Test redaction using dummy secrets.
- Confirm raw legal/user content is not logged by default.
- Verify telemetry failures do not unexpectedly break the core request path unless explicitly required.

## Revisit When

Operational requirements change, telemetry adds unacceptable overhead, privacy risks cannot be adequately controlled, or an approved platform provides the required capabilities more effectively.
