# Task Template

## 1. Metadata

- **Task ID:** [Unique identifier]
- **Type:** [Bootstrap / Feature / Refactor / Bug Fix / Testing / Documentation / Infrastructure]
- **Scope:** [AI Service / Framework / Tillegal Application / Tooling]
- **Priority:** [High / Medium / Low]
- **Status:** [Proposed / Ready / In Progress / Blocked / Done]
- **Owner:** [Person or agent]
- **Related tasks:** [Task IDs or None]

## 2. Objective

Describe the specific outcome this task must achieve.

Avoid implementation details unless they are required constraints.

## 3. Background and References

- **Requirements:** [Relevant requirement IDs or document references]
- **Architecture:** [Relevant approved architecture documents]
- **Code references:** [Relevant modules, files, or interfaces]
- **Related decisions:** [ADR IDs or None]

For each reference, state the relevant section when possible.

Do not invent document IDs, existing modules, or approved decisions.

## 4. Scope

### In Scope

- [Change or behavior included]
- [Change or behavior included]

### Out of Scope

- [Explicitly excluded change]
- [Related work deferred to another task]

## 5. Preconditions and Dependencies

- [Required prior task, component, configuration, or service]
- [Required environment or permission]
- [External dependency, if any]

If a precondition is unknown, mark it as unresolved rather than assuming it is satisfied.

## 6. Functional and Technical Requirements

Describe the required behavior and constraints.

- **Inputs:** [Expected inputs and validation]
- **Processing:** [Required behavior]
- **Outputs:** [Expected outputs or side effects]
- **Error handling:** [Expected failure behavior]
- **Configuration:** [Required settings, if applicable]
- **Architecture constraints:** [Applicable boundaries and interfaces]

For AI-related tasks, specify applicable requirements such as structured output, model access through the shared Model Gateway, bounded retries, evaluation, or observability. Include only requirements relevant to this task.

## 7. Acceptance Criteria

- [ ] **AC-01:** [Observable, verifiable outcome]
- [ ] **AC-02:** [Observable, verifiable outcome]
- [ ] **AC-03:** [Observable, verifiable outcome]

Acceptance criteria must be testable. Avoid vague statements such as "works correctly" without defining how correctness is verified.

## 8. Implementation Guidance

Suggested steps:

1. Inspect the relevant code and project conventions.
2. Confirm dependencies, interfaces, and architectural constraints.
3. Implement the smallest coherent change.
4. Add or update relevant tests.
5. Update documentation if necessary.
6. Review the diff and report verification results.

This section provides guidance; it does not authorize changes that conflict with approved architecture.

## 9. Testing and Verification

- **Unit tests:** [Required scenarios]
- **Integration tests:** [Required scenarios, if applicable]
- **Regression tests:** [Existing behavior to protect]
- **Manual checks:** [Steps, if applicable]
- **AI evaluation:** [Dataset, metrics, or cases, if applicable]

Record actual commands and results after execution. Do not mark tests as passed before they have been run.

## 10. Risks and Open Questions

| Item | Description | Status | Resolution |
|---|---|---|---|
| [Risk/question] | [Impact or missing information] | [Open/Resolved/Accepted] | [Decision or next step] |

Separate confirmed requirements from assumptions and proposed solutions.

## 11. Deliverables

- [ ] Code changes
- [ ] Tests or evaluation cases
- [ ] Configuration changes, if required
- [ ] Documentation changes, if required
- [ ] Verification summary

Remove or mark items that do not apply.

## 12. Completion Report

Complete this section after implementation.

- **Implemented:** [Summary]
- **Files changed:** [List]
- **Checks executed:** [Commands and actual results]
- **Acceptance criteria:** [Met / Partially met / Not met]
- **Known limitations:** [Limitations or None]
- **Follow-up tasks:** [Task IDs or None]

## Definition of Done

- [ ] In-scope acceptance criteria are met or deviations are documented.
- [ ] Relevant tests have been run and results recorded.
- [ ] Changes comply with applicable project rules and approved architecture.
- [ ] Required documentation is updated.
- [ ] Remaining risks and incomplete work are disclosed.