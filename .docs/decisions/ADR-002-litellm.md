# ADR-002: Centralize Model Access Behind LiteLLM

- **Status:** Accepted
- **Date:** 2026-10-26
- **Decision owners:** Tillegal AI Service team

## Context

The AI Service may use multiple model providers and model profiles. Allowing each agent to call provider SDKs directly would duplicate routing, timeout, retry, error handling, usage extraction, and fallback logic.

The project needs a shared model-access layer that permits provider changes while keeping application agents independent of provider-specific response formats.

LiteLLM is the selected implementation for normalizing access to supported providers.

## Decision

Use LiteLLM behind a Tillegal-owned **Model Gateway** abstraction.

Agents and application modules must call the internal gateway interface rather than import LiteLLM or provider SDKs directly.

LiteLLM is an implementation detail of the gateway, not the public contract of the AI Service.

## Constraints

- Define an internal request/response contract independent of provider-specific response objects.
- Centralize model-profile selection, timeouts, retries, fallback, and error normalization.
- Validate structured outputs at application boundaries.
- Record provider/model profile, call duration, outcome, and usage information when available.
- Do not fabricate token or cost values.
- Keep credentials in environment configuration or an approved secret manager.
- Test timeout, rate-limit, malformed-output, and fallback behavior.
- Ensure fallback models satisfy the task's minimum capability and output contract.
- Do not let gateway fallback bypass retrieval, legal reasoning constraints, or citation verification.
- Pin the selected LiteLLM version and review changes before upgrading.

## Alternatives Considered

1. **LiteLLM behind an internal gateway:** centralizes provider integration while preserving a project-owned interface.
2. **Direct provider SDKs in each agent:** may be straightforward for a single provider but duplicates integration logic and policy.
3. **Custom adapter for every provider:** provides greater control but increases implementation and maintenance work.

## Consequences

### Benefits

- Provider-specific behavior is centralized.
- Agents can be tested using a mocked gateway.
- Routing and observability policies can be applied consistently.
- Provider changes should require fewer application-level changes.

### Trade-offs

- Adds a dependency and an abstraction layer.
- Some provider-specific capabilities may not map uniformly.
- The gateway requires its own compatibility and failure-path tests.

## Validation Before Acceptance

- Send a model request through the gateway using a configured profile.
- Verify normalized success and error contracts.
- Test timeouts, rate limits, and bounded fallback.
- Verify secret redaction.
- Confirm application agents do not import provider SDKs directly.
- Review dependency, licensing, and deployment suitability.

## Revisit When

The gateway blocks a required provider capability, adds unacceptable complexity, or another approved inference layer provides the same required contract more effectively.
