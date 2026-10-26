# Architecture Decision Template

## 1. Metadata

- **ADR ID:** ADR-[NUMBER]
- **Status:** [Proposed / Accepted / Rejected / Superseded]
- **Date:** [YYYY-MM-DD]
- **Decision owner:** [Person or team]
- **Related requirements:** [IDs or None]
- **Related architecture documents:** [Document references or None]
- **Supersedes:** [ADR ID or None]
- **Superseded by:** [ADR ID or None]

Use `Accepted` only after the responsible team has approved the decision.

## 2. Context

Describe the problem, engineering need, or constraint that requires a decision.

Include relevant facts such as:

- Existing system structure
- Applicable requirements
- Technical or operational constraints
- Current limitations
- Why the decision is needed now

Separate verified facts from assumptions. Cite relevant documents or code where possible.

## 3. Decision Drivers

List the criteria used to compare options.

Examples, when relevant:

- Correctness and reliability
- Architecture and dependency boundaries
- Security and privacy
- Maintainability
- Performance and scalability
- Cost and resource constraints
- Compatibility with existing components
- Testability and observability
- Implementation complexity

Do not include criteria that are irrelevant to the decision.

## 4. Options Considered

### Option A — [Name]

- **Description:** [How it works]
- **Advantages:** [Benefits]
- **Disadvantages:** [Costs and limitations]
- **Risks:** [Relevant risks]
- **Evidence:** [Documentation, prototype, test, or other supporting evidence]

### Option B — [Name]

- **Description:** [How it works]
- **Advantages:** [Benefits]
- **Disadvantages:** [Costs and limitations]
- **Risks:** [Relevant risks]
- **Evidence:** [Documentation, prototype, test, or other supporting evidence]

### Option C — [Name, if needed]

[Use the same structure.]

Do not invent benchmark results, provider capabilities, or cost estimates. Mark information that has not been verified.

## 5. Decision

**Selected option:** [Option name, or Pending]

**Decision statement:** [One concise statement describing what will be adopted.]

**Rationale:** Explain why the selected option best satisfies the decision drivers and why the alternatives were not selected.

If the ADR is still `Proposed`, describe the preferred option as a recommendation, not as an implemented or approved decision.

## 6. Architecture Impact

Describe the impact on relevant components and boundaries.

- **Components affected:** [List]
- **Interfaces or contracts:** [Changes]
- **Dependencies:** [Added, removed, or changed]
- **Data or state:** [Impact, if applicable]
- **Configuration:** [Impact, if applicable]
- **Security and privacy:** [Impact, if applicable]
- **Observability and operations:** [Impact, if applicable]
- **Documentation:** [Documents that need updating]

For Tillegal AI Service decisions, explicitly assess impacts on the shared Model Gateway, LiteLLM integration, LangGraph orchestration, evaluation, and observability where relevant.

## 7. Consequences

### Positive Consequences

- [Expected benefit]

### Negative Consequences and Trade-offs

- [Accepted limitation or cost]

### Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| [Risk] | [Impact] | [Mitigation or open action] |

## 8. Implementation and Verification

List the work needed to apply and validate the decision.

- [ ] [Implementation task]
- [ ] [Test or prototype]
- [ ] [Documentation update]
- [ ] [Operational or configuration update]

**Verification criteria:**

- [Observable criterion]
- [Observable criterion]

Record actual verification results after execution. An ADR documents a decision; it does not by itself prove the implementation is complete.

## 9. Review and Approval

- **Reviewers:** [Names or roles]
- **Approval status:** [Pending / Approved / Rejected]
- **Approval date:** [Date or Pending]
- **Comments:** [Important review feedback]

## 10. Change History

| Date | Change | Author |
|---|---|---|
| [YYYY-MM-DD] | Initial proposal | [Author] |

## Decision Lifecycle

1. **Proposed:** The option is under discussion and is not yet binding.
2. **Accepted:** The responsible team has approved the decision.
3. **Rejected:** The proposal was considered and not adopted.
4. **Superseded:** A later accepted decision replaces this ADR.

Do not change a decision's status merely because implementation has started. Approval and implementation status are separate.