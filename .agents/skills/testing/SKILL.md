# Testing Skill
---
name: testing
description: Apply a systematic testing workflow to Python modules, LangGraph workflows, model integrations, and AI Service behavior.
---

## Purpose

Provide a reusable procedure for selecting, writing, executing, and reporting tests for Tillegal AI Service.

This skill complements `rules/testing.md` by describing the practical testing workflow.

## When to Use

- Implementing a feature or bug fix.
- Adding tests to existing code.
- Investigating a regression.
- Changing graph behavior or model integration.
- Preparing a change for code review.
- Validating a refactor.

## Procedure

### Step 1: Inspect Existing Tests

Identify:

- Test framework and configuration.
- Test directory structure.
- Existing fixtures and test utilities.
- Commands used by the repository.
- Current coverage and known test limitations where available.

Reuse existing conventions instead of introducing a competing testing framework.

### Step 2: Define Expected Behavior

Translate the task into observable assertions.

Identify:

- Successful behavior.
- Invalid input.
- Boundary conditions.
- Expected errors.
- External dependency failures.
- Compatibility requirements.
- Important regression cases.

If acceptance criteria are ambiguous, ask for clarification when the ambiguity materially changes the test outcome.

### Step 3: Choose the Appropriate Test Level

Use:

- Unit tests for isolated functions, validators, and nodes.
- Contract tests for module boundaries and schemas.
- Integration tests for interactions between real components.
- End-to-end tests for complete supported flows.
- Evaluation tests for model-dependent quality.

Do not label a test by its intended purpose if the actual setup does not exercise that boundary.

### Step 4: Build Deterministic Fixtures

- Use synthetic or approved test data.
- Mock external providers for unit tests.
- Avoid uncontrolled network dependencies.
- Avoid unnecessary sleeps and timing assumptions.
- Keep shared fixtures isolated from unintended mutation.
- Do not include real credentials or sensitive legal cases.

### Step 5: Implement Tests

Follow Arrange–Act–Assert or the existing repository convention.

Ensure assertions verify meaningful outcomes rather than only checking that code executed without raising an exception.

Test the error behavior that callers actually observe.

### Step 6: Execute Tests in Increasing Scope

1. Run the focused test for the changed behavior.
2. Run tests for the affected module or component.
3. Run relevant integration or workflow tests.
4. Run broader regression tests when warranted.
5. Run configured formatting, linting, and type checks where applicable.

Use the project's actual commands and report execution limitations.

### Step 7: Investigate Failures

For each failure:

- Inspect the assertion and traceback.
- Reproduce the failure when feasible.
- Determine whether it reflects a defect, regression, environment problem, or external dependency.
- Fix the underlying issue or report it.
- Do not change the assertion simply to obtain a passing result.

### Step 8: Report Results

State the commands executed and actual results.

Separate passing tests from skipped, blocked, or unexecuted checks. Explain relevant limitations and any remaining coverage gaps.

## AI-Specific Testing

For model-dependent behavior:

- Use deterministic mock responses for ordinary functional tests.
- Keep live-provider tests explicitly identified.
- Test malformed model output and provider failures.
- Evaluate quality using versioned cases and documented criteria.
- Record model and prompt metadata when available and relevant.

For legal use cases, prioritize legal-basis correctness and citation support over stylistic similarity or fluency.

## Guardrails

- Do not invent coverage percentages or acceptance thresholds.
- Do not claim a passing suite proves the whole system is correct.
- Do not remove regression tests without justification.
- Do not make routine tests depend on paid API calls unnecessarily.
- Do not treat an LLM judge as the sole authority for legal correctness.

## Expected Output

Relevant automated tests, actual execution results, identified defects, and a clear statement of remaining test gaps.

## Completion Checklist

- [ ] Existing test conventions were followed.
- [ ] Assertions correspond to expected behavior.
- [ ] Important negative and boundary cases are covered.
- [ ] External dependencies are controlled appropriately.
- [ ] Relevant test suites were executed.
- [ ] Failures and limitations are reported accurately.
