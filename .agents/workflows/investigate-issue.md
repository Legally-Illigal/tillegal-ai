# Investigate Issue Workflow

## Purpose

Investigate a bug, failure, unexpected behavior, or performance problem using reproducible evidence before proposing or implementing a fix.

## When to Use

Use this workflow when a test fails, a service does not start, an API behaves unexpectedly, an AI workflow produces incorrect results, or a performance or reliability issue is reported.

## Inputs

- Issue description and expected behavior
- Actual behavior, error messages, logs, or stack traces
- Steps to reproduce, if available
- Relevant source code, configuration, and test results

## Procedure

### 1. Define the Problem

1. Record the expected and actual behavior.
2. Identify the affected component and observable impact.
3. Record the environment and conditions under which the issue occurs.
4. Separate confirmed facts from hypotheses.
5. Identify what evidence is still needed.

Do not assume the reporter's suspected cause is correct.

### 2. Reproduce or Validate

1. Inspect the relevant code and configuration.
2. Reproduce the issue using the smallest practical test case.
3. Check whether the issue is deterministic, intermittent, or environment-dependent.
4. Inspect related logs, exceptions, and test results.
5. Avoid exposing credentials, personal data, or confidential content while collecting evidence.

If reproduction is impossible, explain the limitation and continue with clearly qualified findings.

### 3. Trace the Failure

Follow the relevant execution path across module boundaries.

Check applicable areas such as:

- Input validation and data parsing
- Control flow and state transitions
- External service calls and timeouts
- Dependency versions and configuration
- Persistence, concurrency, and resource lifecycle
- Error handling and exception propagation
- Existing tests and recent code changes

For LangGraph workflows, inspect state updates, conditional edges, termination conditions, retry limits, and node outputs.

For Model Gateway or LiteLLM integrations, inspect provider configuration, request parameters, timeout behavior, response parsing, and error mapping without logging secrets.

For legal retrieval or citation failures, distinguish retrieval failure, source-version or effective-date issues, citation mapping errors, and unsupported model-generated claims.

### 4. Establish the Root Cause

1. List plausible causes.
2. Test hypotheses using targeted experiments or tests.
3. Identify the cause supported by evidence.
4. Explain the mechanism that produces the observed behavior.
5. State confidence and any remaining uncertainty.

If the evidence is insufficient, report the investigation as inconclusive rather than inventing a root cause.

### 5. Recommend a Fix

Describe:

- The root cause or leading hypotheses
- The proposed correction
- Affected modules and interfaces
- Regression risks
- Tests needed to verify the fix

Prefer a targeted correction over a broad rewrite.

If the fix requires an architectural change, identify the decision needed before implementation.

### 6. Implement and Verify, If Authorized

When implementation is within scope:

1. Add a regression test that captures the failure.
2. Apply the smallest suitable fix.
3. Run the regression test and relevant surrounding tests.
4. Check that the correction does not introduce a new failure.
5. Record actual verification results.

If the task is investigation-only, stop after presenting findings and recommendations.

### 7. Report Findings

Include:

- Problem summary
- Reproduction status
- Evidence collected
- Root cause or unresolved hypotheses
- Recommended or implemented fix
- Tests and results
- Remaining uncertainty and follow-up actions

## Guardrails

- Do not edit code before understanding the failure unless a minimal diagnostic change is necessary.
- Do not confuse correlation with causation.
- Do not hide failed experiments or contradictory evidence.
- Do not increase retry counts as a substitute for diagnosing failures.
- Do not expose secrets or sensitive payloads in logs or reports.
- Do not claim a root cause when evidence only supports a hypothesis.

## Definition of Done

- [ ] Expected and actual behavior are documented.
- [ ] Reproduction status is known or its limitation is explained.
- [ ] Evidence and hypotheses are distinguished.
- [ ] Root cause is supported by evidence, or the investigation is marked inconclusive.
- [ ] Fix or next diagnostic step is clearly defined.
- [ ] Verification results and remaining risks are reported.