# Coding Conventions

## Principles

Follow the repository's established style and formal architecture requirements first. These conventions fill gaps; consequential architecture choices belong in ADRs.

- Prefer small, cohesive modules with explicit responsibilities.
- Use type hints for public functions, workflow state, schemas, and gateway contracts.
- Validate inputs at boundaries; never assume model output is valid because it looks like JSON.
- Put network calls, provider calls, persistence, and other side effects behind explicit interfaces.
- Use dependency injection or equivalent construction boundaries so tests can substitute fakes.
- Avoid hidden global mutable state, import-time network activity, circular imports, and speculative abstractions.
- Do not broaden scope or change public contracts in unrelated tasks.

## Naming and boundaries

- Use descriptive names and follow the configured formatter/linter.
- Name workflow nodes for their responsibility, not for a provider/model.
- Use stable identifiers such as `request_id`, `run_id`, `evidence_id`, `citation_id`, and `document_id` where applicable.
- Keep legal-domain types and rules in Tillegal application modules; generic framework modules should not depend on legal-specific entities.
- Agent modules call the shared Model Gateway, not provider SDKs directly.
- The orchestrator owns workflow progression, routing, termination, and execution budgets.
- Keep HTTP handling, workflow logic, model calls, and persistence out of one large function.

## Model output and evidence

- Define schemas for machine-consumed outputs and validate parsed results.
- Treat user input, retrieved documents, and model-generated text as untrusted.
- Distinguish evidence-backed statements from assumptions, uncertainty, and unsupported claims.
- A model's self-assessment is not proof that an answer or citation is correct.
- Never fabricate source URLs, legal identifiers, verification states, token counts, or costs.
- Represent missing, conflicting, stale, or unreachable evidence explicitly.

## Errors, retries, and fallback

- Use clear error categories or typed results.
- Do not swallow exceptions and return a plausible-looking answer.
- Apply timeouts to external calls and keep retries bounded.
- Avoid retry multiplication across layers; document which layer owns retry policy.
- A fallback model must not bypass schema validation or required legal-citation verification.

## Logging and configuration

- Prefer structured logs with correlation IDs and workflow/node names.
- Record latency, provider/model, token usage, cost, retries, fallback, and stop reasons when available.
- Represent unavailable measurements as unknown/absent, not fabricated zeroes.
- Never log API keys, authorization headers, or confidential prompts/documents by default.
- Keep environment-specific settings outside source code and validate required settings at startup.
- Do not hard-code provider/model identifiers in agent business logic.

## Documentation and pull-request checklist

Update docs when component boundaries, workflow transitions, configuration, output contracts, or operational behavior change. Record durable architecture choices in ADRs.

- [ ] Scope and acceptance criteria are met.
- [ ] Contracts are explicit and validated.
- [ ] Dependencies follow `architecture/dependency-rules.md`.
- [ ] Normal, boundary, and failure paths are tested.
- [ ] Unit tests mock provider calls.
- [ ] Logs/errors do not leak secrets or sensitive content.
- [ ] Timeouts, retries, and workflow budgets are bounded.
- [ ] Relevant docs and ADRs are updated.
