# Code Review Skill
---
name: code-review
description: Conduct evidence-based reviews of code changes for correctness, architecture, security, maintainability, and regression risk.
---

## Purpose

Provide a repeatable, evidence-based method for reviewing changes to Tillegal AI Service.

The purpose of a review is to identify meaningful problems before integration, not to rewrite code according to personal preferences.

## When to Use

- Reviewing a feature or bug fix.
- Reviewing a pull request or change set.
- Checking an architecture-sensitive modification.
- Validating a refactor.
- Performing a final review before release.

## Procedure

### Step 1: Establish Review Context

Read:

- Task description and acceptance criteria.
- Complete change diff.
- Relevant project rules.
- Approved architecture documentation and applicable ADRs.
- Related implementation and tests.

Identify the intended scope before evaluating the change.

### Step 2: Trace the Changed Behavior

Follow changed functions, interfaces, state transitions, and external calls through relevant call sites.

Check whether the implementation satisfies the required behavior and whether its assumptions hold in the actual runtime context.

### Step 3: Review Correctness

Look for:

- Incorrect control flow.
- Missing or invalid state.
- Incorrect data transformations.
- Contract mismatches.
- Unhandled failure paths.
- Incorrect assumptions about provider responses.
- Compatibility regressions.
- Missing timeout or termination conditions.

Prioritize issues that can cause incorrect results, crashes, data loss, or misleading output.

### Step 4: Review Architecture

Check:

- Module responsibilities.
- Dependency direction.
- Model Gateway usage.
- Separation between generic framework and legal-specific behavior.
- Unnecessary coupling or duplicated abstractions.
- Consistency with approved design decisions.

Do not reject a change solely because it differs from a personal architectural preference when the design is valid and within the approved constraints.

### Step 5: Review Security and Privacy

Check for:

- Secrets in code or configuration.
- Sensitive information in logs.
- Unsafe handling of retrieved or user-provided content.
- Missing validation or authorization checks.
- Unsafe file or tool operations.
- Unapproved external data transmission.
- Insecure fallback behavior.

### Step 6: Review Tests

Verify that tests exercise the changed behavior and relevant failure paths.

Distinguish actual execution evidence from statements in a task report. Do not assume all tests ran because a test file exists.

### Step 7: Review Legal AI Behavior

When relevant, verify that:

- Citation provenance is preserved.
- Citation formatting is not confused with verification.
- Required legal-source applicability checks are maintained.
- Missing evidence does not become fabricated certainty.
- Reflection or judge nodes do not bypass explicit validation.

### Step 8: Report Findings

For each actionable finding, provide:

- Severity.
- File and relevant code location.
- Description of the defect or risk.
- Concrete impact.
- Supporting evidence.
- Recommended correction.

Avoid vague findings that merely say a change "could be better."

### Step 9: State the Outcome

Use a clear review result:

- **Request changes:** material defects or blockers remain.
- **Approve with observations:** no identified blocker, but non-blocking issues or limitations remain.
- **Approve:** no material issue was identified within the review scope and available evidence.

An approval is not a guarantee of defect-free behavior.

## Severity Guidance

- **Critical:** severe security, data-integrity, or correctness failure with major impact.
- **High:** major functional or architectural defect that should block integration.
- **Medium:** meaningful defect with a narrower impact or a significant maintainability risk.
- **Low:** minor issue with limited impact.

Adjust severity to actual impact and evidence. Do not inflate severity to emphasize a preference.

## Guardrails

- Do not invent findings.
- Do not report speculative concerns as confirmed defects.
- Do not hide critical issues among minor style comments.
- Do not modify unrelated code in a review-only task.
- Do not claim a test passed without execution evidence.

## Expected Output

A prioritized review report with actionable findings, an explicit outcome, and a truthful account of validation evidence.

## Completion Checklist

- [ ] The diff and relevant surrounding code were inspected.
- [ ] Requirements and architectural constraints were considered.
- [ ] Correctness and security risks were assessed.
- [ ] Tests and validation evidence were reviewed.
- [ ] Findings include concrete evidence and actionable recommendations.
- [ ] Review outcome and limitations are explicit.
