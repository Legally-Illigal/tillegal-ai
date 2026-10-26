# Testing Rules

## 1. Purpose

These rules define how coding agents should validate changes to Tillegal AI Service.

Testing must establish observable behavior and expose regressions. A successful test run is evidence for the behaviors covered by those tests; it is not proof that the entire system is correct.

Inspect the existing test framework, directory structure, and execution commands before adding or changing tests.

## 2. Testing Principles

- Test behavior and contracts, not just implementation details.
- Prefer deterministic tests that can be repeated reliably.
- Keep unit tests independent of external model providers and network services.
- Use integration tests to verify interactions between real components at defined boundaries.
- Keep slow, expensive, and nondeterministic evaluations separate from fast unit tests where practical.
- Never delete or weaken a test merely to make a change pass.
- Do not claim a test passed unless its execution result supports that claim.

## 3. Test Categories

Use the categories that fit the change and the repository's actual capabilities.

### Unit Tests

Test individual functions, nodes, validators, routing conditions, and transformations in isolation.

Cover:

- Normal behavior.
- Boundary conditions.
- Missing or invalid input.
- Expected exceptions.
- Fallback behavior.
- Retry limits and termination conditions.

### Contract Tests

Verify that components agree on input and output schemas, required fields, error representations, and serialization behavior.

For model-facing contracts, include malformed, incomplete, or unexpected responses.

### Integration Tests

Verify relevant interactions among components, such as:

- Agent nodes and LangGraph state.
- Workflows and the Model Gateway.
- Provider adapters and normalized responses.
- Configuration loading and startup validation.
- Observability hooks and execution metadata.

Use controlled test dependencies where live services are not necessary.

### End-to-End Tests

Where the environment supports them, test complete user-facing flows through the relevant runtime boundaries.

Do not label a mocked workflow test as a full end-to-end test.

### Evaluation Tests

Use evaluation datasets and metrics for model-dependent quality.

Separate deterministic functional assertions from model-quality judgments. Track the dataset and evaluation configuration used for each meaningful result.

## 4. LangGraph Testing

For graph workflows, test:

- Initial state and required state fields.
- Node behavior and state updates.
- Conditional routing.
- Successful terminal paths.
- Error paths and fallback paths.
- Maximum retry or reflection cycles.
- Missing, malformed, or contradictory node output.
- Cancellation and timeout behavior where applicable.
- State persistence or resume behavior only when supported by the implementation.

Verify that graph execution terminates under expected failure conditions. Avoid tests that depend on arbitrary sleep durations when synchronization or direct state assertions can be used.

## 5. Model Gateway and LLM Testing

Unit tests should mock provider responses at the Model Gateway or adapter boundary.

Cover:

- Successful invocation.
- Timeout and connection failures.
- Rate limiting and provider errors.
- Invalid or incomplete model output.
- Structured output validation.
- Retry eligibility and maximum attempts.
- Fallback behavior, if configured.
- Missing usage metadata.
- Safe handling of provider errors.

Do not require live API keys or chargeable provider calls for ordinary unit tests.

Live-provider tests must be explicitly identified, opt-in where appropriate, and configured to avoid unnecessary cost or sensitive-data exposure.

## 6. Legal AI Quality Testing

For legal-domain behavior, evaluation must give priority to the legal basis and citation.

Test relevant cases for:

- Whether a cited source exists.
- Whether the cited provision supports the claim.
- Whether the provision is applicable to the scenario.
- Whether effective dates, amendments, or revocation status are handled correctly when the required source data is available.
- Whether the answer distinguishes verified facts from assumptions.
- Whether insufficient evidence results in appropriate uncertainty.
- Whether the response fabricates citations or verification claims.

A correct conclusion with an incorrect or inapplicable legal basis must not be treated as a fully correct result.

Do not rely exclusively on LLM-as-a-judge or Self-Reflection to verify legal correctness. Use authoritative source data and explicit evaluation criteria wherever available.

## 7. Test Data and Security

- Use synthetic or approved test data.
- Do not commit API keys, production credentials, or unnecessary personal data.
- Avoid including confidential user content in test fixtures.
- Sanitize logs and test artifacts when they may contain sensitive information.
- Do not make tests dependent on private user data or uncontrolled external websites.

## 8. Regression and Quality Gates

For each change:

1. Run the most relevant focused tests.
2. Run additional tests required by the affected components.
3. Run configured linting, formatting, and type checks when applicable.
4. Run broader regression tests when the change affects shared interfaces, orchestration, security, or runtime behavior.
5. Review failures and distinguish new regressions from pre-existing failures.
6. Record any checks that could not be executed.

Do not invent numeric coverage thresholds or evaluation acceptance thresholds. Use approved project configuration or requirements; otherwise, identify the threshold as a proposal requiring confirmation.

## 9. Reporting Results

A test report should state:

- Commands or test suites executed.
- Pass, fail, skipped, and blocked results where available.
- Relevant environment or dependency limitations.
- Known failures and whether they appear related to the change.
- Remaining test gaps.

## 10. Completion Checklist

- [ ] New behavior has appropriate tests.
- [ ] Failure and boundary cases are covered where relevant.
- [ ] Tests do not depend unnecessarily on live LLM services.
- [ ] Legal quality checks prioritize source and citation correctness.
- [ ] Relevant regression and quality checks have been executed.
- [ ] Results are reported accurately.
