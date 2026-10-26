# LangGraph Development Skill
---
name: langgraph-development
description: Design, implement, and test LangGraph nodes, state, routing, and bounded Multi-Agent workflows.
---

## Purpose

Guide the development of reliable, testable graph workflows for Tillegal AI Service.

Use the installed LangGraph version and approved architecture as the source for implementation details. Do not assume that APIs or capabilities from another version are available.

## When to Use

- Creating a graph workflow.
- Adding or modifying a node.
- Defining graph state.
- Adding conditional routing.
- Implementing retry, fallback, or reflection behavior.
- Integrating graph execution with the Model Gateway.
- Adding checkpointing or resume support when required.

## Procedure

### Step 1: Define the Workflow

Identify:

- Workflow purpose.
- Entry point and expected final output.
- Required state fields.
- Nodes and their responsibilities.
- Routing conditions.
- Terminal states.
- Expected failure paths.

Use the approved requirements. Do not invent additional agents or stages without a justified need.

### Step 2: Define State

For each state field, determine:

- Name and type.
- Whether it is required or optional.
- Which node produces it.
- Which nodes consume it.
- How updates are applied.
- Whether it may contain sensitive information.

Avoid duplicating data unnecessarily or storing secrets in graph state.

### Step 3: Define Node Contracts

Each node should have a clear responsibility and an explicit contract.

Specify:

- Required inputs.
- Produced state updates.
- Possible errors.
- External side effects.
- Dependencies.
- Whether execution may be retried safely.

Keep provider-specific behavior behind the Model Gateway.

### Step 4: Implement Routing and Termination

- Use explicit conditions for conditional edges.
- Ensure every expected execution path has a valid destination.
- Define when the graph terminates.
- Bound retry and reflection cycles.
- Handle invalid state and missing node outputs.
- Define behavior when retry limits are exhausted.

Do not create loops without an explicit termination condition.

### Step 5: Implement Error Handling

Distinguish recoverable failures from permanent failures.

Examples include:

- Invalid input or state.
- Model-provider timeout.
- Rate limiting.
- Structured-output validation failure.
- Missing retrieval results.
- Exhausted retry attempts.

Apply retries only where appropriate. Do not retry permanent validation or authorization failures without a corrective action.

### Step 6: Add Tests

Test:

- Initial state.
- Individual node behavior.
- State updates.
- Conditional routing.
- Successful completion.
- Error and fallback paths.
- Retry limits.
- Termination after failure.
- Persistence or resume behavior if implemented.

Prefer deterministic node and graph tests over tests that depend on live model calls.

### Step 7: Verify Integration

Check that:

- Graph nodes use approved interfaces.
- Model calls pass through the Model Gateway.
- Application-specific policies remain in the correct layer.
- Observability captures useful execution context.
- Sensitive information is handled appropriately.

## Reflection and Judge Nodes

Reflection can help identify incomplete reasoning, missing information, or unsupported claims. It does not prove correctness.

For legal workflows, citation and legal-basis correctness must be checked against appropriate source evidence and explicit validation criteria wherever available.

Do not allow a positive reflection result to bypass mandatory verification.

## Guardrails

- Do not assume graph execution is automatically idempotent or replay-safe.
- Do not assume checkpointing is configured.
- Do not place unrelated business logic inside a node.
- Do not introduce unbounded recursion, retries, or agent cycles.
- Do not treat model-generated output as trusted state without validation.

## Expected Output

A clearly defined workflow, explicit state and node contracts, bounded execution paths, relevant tests, and workflow documentation.

## Completion Checklist

- [ ] State and node responsibilities are explicit.
- [ ] Routing and terminal paths are defined.
- [ ] Retries and loops are bounded.
- [ ] Errors and malformed outputs are handled.
- [ ] Tests cover normal and exceptional paths.
- [ ] Model calls respect the gateway boundary.
- [ ] Legal verification is not replaced by reflection.
