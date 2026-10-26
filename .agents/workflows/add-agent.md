# Add Agent Workflow

## Purpose

Introduce a new agent into the AI Service's LangGraph-based runtime only when a distinct responsibility justifies it, with explicit contracts, bounded execution, and measurable behavior.

## When to Use

Use this workflow when adding a new runtime agent or node to an existing AI workflow.

Do not use it when adding a coding-assistant role under `.agents/agents/`. Coding-harness agents and runtime agents are different concepts.

## Inputs

- Feature or task requirements
- Approved system architecture
- Existing graph, state schema, node implementations, and routing logic
- Model Gateway and evaluation conventions
- Relevant tests and observability facilities

## Procedure

### 1. Justify the Agent

Define:

- The responsibility it owns
- The problem it solves
- Its expected input and output
- Why the responsibility cannot be handled adequately by an existing node or ordinary function
- Its dependencies and failure modes

Avoid adding agents merely to increase the number of steps or imitate a multi-agent pattern.

### 2. Define the Contract

Specify:

- Input schema and required fields
- Output schema and required fields
- State fields read and written
- Validation and failure behavior
- Whether the node calls an LLM or performs deterministic processing
- Expected timeout, retry, and termination behavior

Prefer structured, validated contracts over undocumented free-form state.

### 3. Design the Graph Integration

1. Identify the entry point and downstream consumers.
2. Define the normal path and conditional routing.
3. Define how failures and invalid outputs are handled.
4. Define explicit termination conditions.
5. Set bounded retry or revision limits.
6. Check that no cycle can continue indefinitely.

Any return edge, such as sending a judge result back to a query or retrieval node, must have a clear stopping condition.

### 4. Implement the Node

1. Follow existing project conventions.
2. Keep orchestration, prompting, model access, and domain-specific logic in their designated modules.
3. Use the shared Model Gateway for model calls where required.
4. Validate inputs before execution and outputs before updating shared state.
5. Handle expected errors explicitly.
6. Avoid hidden side effects and mutation of unrelated state.
7. Add structured logging and relevant execution metrics without exposing sensitive payloads.

### 5. Add Tests

Include relevant tests for:

- Valid inputs and expected outputs
- Missing or invalid fields
- Model failure or malformed output, if applicable
- Routing decisions
- Retry limits and termination
- State updates and downstream compatibility
- Regression behavior of the existing graph

Use deterministic mocks or fixtures where appropriate. Do not rely exclusively on live LLM calls for basic control-flow tests.

### 6. Add Evaluation Coverage

Define what success means for the agent and how it will be measured.

Depending on its role, evaluate:

- Output schema validity
- Classification or routing accuracy
- Retrieval relevance
- Evidence coverage
- Latency and token usage
- Error and fallback behavior

For legal-related agents, include evaluation cases that detect unsupported legal claims, invalid or outdated legal grounds, and incorrect citation mapping. Self-reflection may identify potential problems but does not independently verify legal correctness.

### 7. Integrate and Document

Update the relevant:

- Graph definition and routing
- State and output schemas
- Configuration
- Tests and evaluation cases
- Observability events or metrics
- Architecture documentation, if the architecture changes

Create or update an architecture decision record if the change requires a new architectural decision. Keep its status consistent with the team's actual approval.

### 8. Verify the Full Workflow

Run targeted tests, graph-level tests, and relevant regression tests.

Confirm that the new agent does not introduce unbounded loops, unexpected state changes, or unnecessary model calls.

## Guardrails

- Do not confuse runtime agents with coding-harness agents.
- Do not add an agent without a distinct responsibility.
- Do not allow unbounded graph cycles or retries.
- Do not bypass the shared Model Gateway without an approved architectural reason.
- Do not treat LLM-generated judgments as authoritative facts.
- Do not mix generic framework behavior with Tillegal-specific legal rules without an explicit design reason.

## Definition of Done

- [ ] Agent responsibility is justified.
- [ ] Input, output, and state contracts are explicit.
- [ ] Graph routing and termination are bounded.
- [ ] Error handling and observability are implemented.
- [ ] Unit and graph-level tests are added or updated.
- [ ] Evaluation coverage reflects the agent's responsibility.
- [ ] Documentation and architecture decisions are updated where necessary.