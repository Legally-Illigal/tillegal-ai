# ADR-001: Use LangGraph for Workflow Orchestration

- **Status:** Accepted
- **Date:** 2026-10-26
- **Decision owners:** Tillegal AI Service team

## Context

The AI Service requires multi-step workflows for query analysis, evidence retrieval, evidence sufficiency assessment, answer generation, and legal-basis/citation verification.

These workflows need explicit transitions, conditional paths, bounded loops, observable execution, and testable state contracts. The orchestration mechanism should support Tillegal's legal workflows without coupling the entire reusable framework to legal-specific logic.

LangGraph is the selected workflow orchestration implementation.

## Decision

Use LangGraph as the workflow orchestration implementation.

Keep application-specific legal behavior in Tillegal application modules. Keep workflow state, node contracts, and framework-specific dependencies behind explicit boundaries where practical.

## Constraints

- Define validated workflow state and node input/output contracts.
- Bound workflow steps, loops, retries, execution time, and resource consumption.
- Record node outcomes, transitions, and stop reasons.
- Treat retrieved documents and tool outputs as untrusted data.
- Do not allow routing or fallback to bypass legal-basis and citation verification.
- Keep model-provider calls behind the shared Model Gateway.
- Test graph transitions and failure paths without requiring live model calls.
- Avoid exposing LangGraph-specific types throughout unrelated application modules.

## Alternatives Considered

1. **LangGraph:** provides graph-based orchestration and conditional transitions.
2. **Hand-written orchestration:** provides direct control but requires the team to implement and maintain transition handling, execution limits, and observability.
3. **Another agent framework:** may offer useful abstractions but requires evaluation of control-flow transparency, testability, dependencies, and runtime behavior.

No comparative benchmark is claimed by this ADR.

## Consequences

### Benefits

- Workflow paths and conditional transitions can be inspected and tested.
- Retrieval and verification loops can be explicitly bounded.
- Node-level observability can be implemented consistently.

### Trade-offs

- The team must learn and maintain LangGraph-specific concepts.
- Framework-specific APIs may create coupling if boundaries are not maintained.
- Framework upgrades may change execution behavior and require regression tests.

## Validation Before Acceptance

- Prototype the core workflow.
- Test a bounded conditional loop.
- Test provider errors, invalid node outputs, cancellation, and maximum-step termination.
- Confirm correlation IDs and node-level execution information are available.
- Review dependency, licensing, and deployment suitability.
- Verify consistency with the project's documented architecture and implementation constraints.

## Revisit When

Reconsider this decision if LangGraph prevents required runtime behavior, introduces disproportionate complexity, or no longer fits the workflow requirements.
