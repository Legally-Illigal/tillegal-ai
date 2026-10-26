# Bug Report Template

## 1. Metadata

- **Bug ID:** [Unique identifier]
- **Status:** [New / Investigating / Confirmed / Fix In Progress / Resolved / Cannot Reproduce]
- **Severity:** [Critical / High / Medium / Low]
- **Priority:** [High / Medium / Low]
- **Affected component:** [Module or service]
- **Environment:** [Local / Test / Demo / Other]
- **Reported by:** [Person or agent]
- **Related task or issue:** [ID or None]

## 2. Summary

Describe the observed problem in one or two sentences.

State what is failing without assuming the cause.

## 3. Expected Behavior

Describe what should happen based on the relevant requirement, interface contract, or approved design.

**Reference:** [Requirement, acceptance criterion, or documentation section]

If expected behavior is not documented, mark it as needing clarification.

## 4. Actual Behavior

Describe what actually happens.

- **Observed result:** [Actual output or behavior]
- **Error message:** [Exact relevant message, if available]
- **Frequency:** [Always / Intermittent / Once / Unknown]
- **Impact:** [Affected functionality or users]

Preserve the original error text when useful. Redact secrets and sensitive information.

## 5. Steps to Reproduce

1. [Initial state or prerequisite]
2. [Action]
3. [Action]
4. [Observed failure]

- **Reproducible:** [Yes / No / Partially / Not tested]
- **Reproduction notes:** [Conditions or limitations]

If the issue cannot be reproduced, document the attempts and available evidence.

## 6. Evidence

- **Logs:** [Relevant redacted log reference or excerpt]
- **Stack trace:** [Relevant excerpt or reference]
- **Test result:** [Failing test or command, if available]
- **Related files:** [File paths or module names]
- **Recent changes:** [Relevant commit, change, or Unknown]

Do not include credentials, access tokens, private keys, or unnecessary user data.

## 7. Investigation

### Confirmed Facts

- [Fact supported by reproducible behavior or evidence]

### Hypotheses

- [Possible cause and supporting evidence]
- [Alternative cause, if relevant]

### Root Cause

[Confirmed explanation, or "Not yet established"]

Do not label a hypothesis as the root cause until sufficient evidence supports it.

## 8. Proposed Fix

- **Approach:** [Proposed correction]
- **Affected components:** [Modules or interfaces]
- **Regression risks:** [Potential side effects]
- **Required tests:** [Tests that should verify the fix]

If the fix requires an architectural change, identify the decision that must be made before implementation.

## 9. Verification After Fix

Complete this section after the fix is implemented.

- **Fix reference:** [Commit, task ID, or change reference]
- **Regression test:** [Command and actual result]
- **Related tests:** [Commands and actual results]
- **Manual verification:** [Steps and result, if applicable]
- **Remaining limitations:** [Known issues or None]

## 10. Resolution

- **Resolution:** [Fixed / Duplicate / Cannot Reproduce / Deferred / Not a Bug]
- **Evidence supporting resolution:** [Test results or other evidence]
- **Follow-up work:** [Task IDs or None]

## Completion Checklist

- [ ] Expected and actual behavior are documented.
- [ ] Reproduction steps and environment are recorded.
- [ ] Evidence is available and sensitive information is redacted.
- [ ] Facts and hypotheses are distinguished.
- [ ] Root cause is confirmed or explicitly unresolved.
- [ ] Fix and regression verification are documented.
- [ ] Resolution status reflects the available evidence.