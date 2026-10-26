# Testing Guide

## Goals

Test both software correctness and AI behavior. For Tillegal, correct legal grounds and citations outrank fluent wording. A plausible answer with an incorrect, repealed, or unsupported legal basis is not a successful result.

## Test layers

### Unit tests

Test input normalization, schema validation, deterministic routing, evidence/citation identity handling, gateway request/response normalization, error mapping, configuration validation, and redaction. Use fakes/mocks for providers, retrieval, persistence, and external services. Unit tests must not require live API keys or network access.

### Contract tests

Check API schemas, agent input/output, workflow state and transitions, normalized gateway responses, retrieval metadata, and citation-verification states. Include malformed, partial, unexpected, and version-mismatched data. Contract validity does not prove factual correctness.

### Integration tests

Test real component boundaries where practical: orchestrator and nodes, gateway and configured adapter, retrieval backend, persistence/evaluation recording if implemented, and API-to-workflow serialization. Mark provider-dependent tests explicitly. Never silently turn a mock test into a paid live call.

### Workflow tests

Use deterministic node outputs to test:

- Normal successful completion.
- Missing information or insufficient evidence.
- Search judged insufficient and a bounded retrieval retry.
- Conflicting, unsupported, or unverified citations.
- Model timeout, provider failure, and fallback.
- Invalid structured output.
- Maximum retry/step budget reached.
- Cancellation or internal failure, where supported.

Assert the final result and the path taken, verification state, retry count, stop reason, and whether required checks were skipped.

## AI quality evaluation

Use a versioned evaluation set with representative queries and expected evidence, citations, or grading criteria. Record model/profile, prompt version, retrieval configuration, workflow version, dataset version, date, and relevant run metadata.

| Dimension | Evaluation question |
|---|---|
| Legal-basis accuracy | Is the legal basis relevant and correct? |
| Citation validity | Does the citation identify the source and supporting passage accurately? |
| Current validity | Is the instrument in force for the relevant date, when reliable status data exists? |
| Evidence support | Are material claims supported by retrieved evidence? |
| Scenario application | Are facts applied correctly and missing facts acknowledged? |
| Completeness | Are material limitations or qualifications omitted? |
| Uncertainty | Does the system admit when evidence is insufficient? |
| Operations | What are latency, failure, retries, token usage, and cost where measurable? |

Prioritize evaluation failures consistently:

1. Wrong, inapplicable, revoked, or non-supporting legal basis.
2. Incorrect application of law to the scenario or fabricated material facts.
3. Misleading or incorrect verification status.
4. Missing material caveat, uncertainty, or limitation.
5. Wording, structure, and style issues that do not change legal meaning.

A correct conclusion does not compensate for a wrong legal basis. Self-Reflection can flag potential issues but is not independent proof of correctness.

Do not invent quality thresholds without an agreed baseline or project decision. Report metric, sample size, dataset version, and test conditions together.

## Data and repeatability

- Use synthetic or approved, redacted data in ordinary development.
- Do not commit personal data, confidential consultations, API keys, or raw provider traces.
- Track dataset provenance and permitted use.
- Include instruction-like content in retrieved documents to verify it is treated as untrusted data.
- Do not assume a retrievable public source is current.
- Use deterministic fixtures for unit/workflow tests. Live model evaluations are nondeterministic; record configuration and acknowledge provider-side changes.

## Suggested sequence

Use actual commands from the repository configuration, not invented commands:

1. Formatting and lint checks.
2. Static type checks, if configured.
3. Unit tests.
4. Contract tests.
5. Offline workflow tests.
6. Available integration tests.
7. Explicitly selected live-provider smoke tests.
8. Quality evaluation against the approved dataset.

## Completion checklist

- [ ] Normal and failure paths are covered.
- [ ] Unit tests run without live credentials.
- [ ] Retry and workflow limits are asserted.
- [ ] Citation-verification states are asserted.
- [ ] Fallback cannot bypass required checks.
- [ ] Logs/artifacts contain no secrets.
- [ ] Relevant AI behavior is evaluated on an appropriate dataset.
- [ ] Results are traceable to code, prompt, workflow, and dataset versions.
