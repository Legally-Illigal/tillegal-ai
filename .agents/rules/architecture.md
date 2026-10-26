# Architecture Rules

## 1. Purpose

These rules protect the architecture, dependency boundaries, and extensibility of Tillegal AI Service.

Project architecture documentation and accepted architecture decisions are authoritative. An ADR marked `Proposed` is not accepted. These rules do not authorize an agent to redesign the system independently.

## 2. Architecture Discovery

Before making architectural changes:

1. Inspect the current repository structure.
2. Read the relevant architecture documentation.
3. Identify existing module boundaries and dependency directions.
4. Check whether the proposed change conflicts with an approved decision.
5. Determine whether the change is local implementation work or requires architectural approval.

Do not assume that a proposed directory structure, ADR, or design discussion has already been implemented or approved.

If documentation and code disagree, report the discrepancy and determine the intended source of truth before making a broad change.

## 3. Separation of Responsibilities

Preserve clear responsibilities between components.

### Orchestration

LangGraph is the intended orchestration technology for agent workflows, subject to confirmation against approved architecture decisions.

Workflow code should define state transitions, control flow, routing, and execution boundaries. Avoid embedding unrelated infrastructure or provider-specific logic into workflow nodes.

### Model Gateway

Model invocation should go through the shared Model Gateway rather than being independently implemented in each agent.

The gateway is responsible for the approved shared model-calling contract and provider integration boundary. Provider-specific configuration and SDK behavior should remain behind this boundary.

### Agents

An agent should have a clear responsibility and a defined input/output contract.

Agent implementations should not become containers for unrelated orchestration, persistence, provider configuration, and application business logic.

### Application-Specific Logic

Keep reusable framework behavior separate from legal-domain policies, legal prompts, source retrieval, citation verification, and legal evaluation logic.

### API and Runtime

Keep API transport concerns, workflow execution, model invocation, and application policies separated according to the approved architecture.

Do not introduce a new service, process, or deployment boundary without a requirement or justified architecture decision.

## 4. Dependency Rules

- Dependencies must follow the approved architecture.
- Reusable framework modules must not depend unnecessarily on Tillegal-specific application logic.
- Provider SDKs should not leak into agent implementations when the Model Gateway can provide the required abstraction.
- Avoid circular imports and circular module dependencies.
- Do not use global mutable state as an implicit communication mechanism between agents.
- Pass dependencies explicitly through approved constructors, factories, runtime contexts, or dependency-injection mechanisms.
- Avoid importing internal implementation details from unrelated modules when a stable public interface exists.

If the current repository does not yet establish a boundary or interface, propose the smallest reasonable design and document the assumption.

## 5. LangGraph Workflow Rules

When implementing graph workflows:

- Define state fields and their ownership clearly.
- Make node inputs, outputs, and side effects explicit.
- Use structured routing conditions rather than fragile string matching where practical.
- Ensure conditional edges and terminal paths are intentional.
- Bound retries, reflection cycles, and re-routing loops.
- Define behavior for missing state, invalid output, node exceptions, and exhausted retries.
- Keep external side effects visible and controlled.
- Do not assume that graph execution is safe to resume or replay unless the relevant nodes and persistence mechanisms support it.
- Do not store unnecessary sensitive content in persistent graph state.

A Self-Reflection node may identify weaknesses or request further processing. It must not independently establish that a legal conclusion or citation is correct.

## 6. Contracts and Error Handling

Use explicit, validated contracts at module boundaries.

- Validate external input before it enters a workflow.
- Validate structured model output before downstream use.
- Represent expected failures using the repository's established error-handling conventions.
- Preserve enough context for diagnosis without leaking secrets or sensitive content.
- Do not silently convert an invalid or incomplete model response into a valid-looking answer.
- Keep retry behavior bounded and specific to recoverable failures.

Avoid coupling modules to private implementation details or unstable provider response formats.

## 7. Configuration and Extensibility

- Keep environment-specific configuration outside source code.
- Do not hardcode provider credentials, model endpoints, or deployment-specific values.
- Prefer explicit configuration and stable interfaces over hidden conventions.
- Add new providers through the approved gateway extension mechanism.
- Add new agents through the established workflow and contract patterns.
- Avoid building speculative plugin systems or abstractions without a demonstrated requirement.

## 8. Architecture Changes

For a change affecting module boundaries, shared contracts, orchestration strategy, provider integration, persistence, security boundaries, or deployment topology:

1. Describe the current behavior.
2. Explain the problem or requirement.
3. Present the proposed change and alternatives where relevant.
4. Identify affected components and compatibility risks.
5. Identify testing and migration requirements.
6. Update or propose an ADR when appropriate.
7. Obtain required approval before treating the design as authoritative.

Do not silently edit approved architecture documentation to justify a code change.

## 9. Architecture Review Checklist

Before completing an architectural change, verify:

- [ ] Responsibilities remain clear.
- [ ] Dependency directions are valid.
- [ ] Public contracts are explicit.
- [ ] Error paths and retry bounds are defined.
- [ ] Security and observability implications are considered.
- [ ] Relevant tests cover the changed boundaries.
- [ ] Documentation and ADR status accurately reflect the decision.
