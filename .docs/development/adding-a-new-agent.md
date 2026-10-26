# Adding a New Agent

## Purpose

Use this guide to add a bounded agent/node without breaking framework boundaries. An “agent” means a workflow responsibility; it does not automatically imply an autonomous loop or separate service. If a behavior is deterministic transformation or validation, a regular function/service may be simpler and safer.

## 1. Define the responsibility

Document the problem, inputs, outputs, side effects, failure modes, completion condition, call/retry/graph-visit budget, and quality risks. Avoid giving one agent unrelated responsibilities such as query interpretation, retrieval, legal reasoning, and final citation verification.

## 2. Choose the correct layer

- **Reusable framework:** generic orchestration helpers, shared schemas, model-gateway contracts, telemetry, evaluation infrastructure.
- **Tillegal application layer:** legal query interpretation, legal retrieval policy, legal answer generation, legal evidence assessment, citation verification.
- **API layer:** HTTP request/response concerns.
- **Infrastructure adapter:** provider, database, retrieval backend, or other external integration.

Choose the narrowest layer that owns the responsibility. Do not add legal-domain types to generic framework modules without an explicit architectural reason. Follow `architecture/dependency-rules.md`.

## 3. Define typed contracts first

Specify required/optional fields, stable identifiers and provenance, allowed status values, uncertainty/failure representation, and versioning if data is persisted or exchanged externally. Validate model output before it enters workflow state. Avoid an unstructured dictionary as the only contract between major components when a typed schema is practical.

## 4. Implement a bounded unit

A node should validate its required input, call only the interfaces it needs, return a structured result or documented failure, emit useful telemetry, avoid mutating unrelated state, and respect timeouts/retry/execution budgets. Use the shared Model Gateway for all LLM calls; do not import provider SDKs directly. Do not add an LLM if the behavior does not need one.

Illustrative pseudocode only; adapt names to the actual repository:

```python
async def example_node(state: WorkflowState) -> dict:
    # Validate inputs required by this node.
    # Call an injected service or shared Model Gateway if needed.
    # Validate any model-generated structured output.
    # Return only the state updates owned by this node.
    return {"example_result": validated_result}
```

This example does not declare actual project class names or runtime APIs.

## 5. Register the node in the workflow

If LangGraph is the adopted orchestrator, follow the existing graph construction pattern rather than introducing a second orchestration mechanism.

- Register a stable name based on responsibility.
- Define incoming/outgoing transitions and explicit routing conditions.
- Define behavior for missing inputs and failures.
- Ensure every path reaches a valid completion or controlled stop.
- Enforce graph/step budgets to prevent infinite loops.
- Ensure fallback and error routes cannot bypass required legal verification.
- Do not route based on hidden mutable global state.

## 6. Add prompts/configuration only when needed

For model-backed nodes, store prompts in the established prompt location; define their purpose/versioning; specify output schema and insufficient-evidence behavior; treat user/retrieved content as untrusted; and configure model profile, timeout, and token limits outside business logic. Do not put secrets or environment-specific endpoints in prompts.

## 7. Test the agent

At minimum, test valid input/output, invalid or missing input, malformed model output where applicable, insufficient/conflicting evidence, external failure, timeout and bounded retries, correct workflow routing, telemetry, and redaction. Use a fake Model Gateway in unit tests. Keep live-provider tests separate and explicitly selected.

## 8. Evaluate quality

Evaluate model/retrieval-backed behavior on representative examples and record prompt/model/workflow versions. For legal responsibilities, evaluate evidence and citation correctness—not just fluent text. Self-Reflection can flag potential failures but cannot replace source verification.

## 9. Update documentation

Update only the relevant docs:

- `architecture/component-design.md` for responsibility/contract changes.
- `architecture/runtime-flow.md` for workflow order, branches, or termination changes.
- `architecture/dependency-rules.md` for dependency-boundary changes.
- `architecture/evaluation-design.md` for evaluation responsibility or metrics changes.
- `architecture/observability-design.md` for new events or measurements.
- Relevant ADRs for durable technology/architecture decisions.

Keep implementation guidance concise and avoid duplicating existing architecture documentation.

## Checklist

- [ ] Responsibility is distinct and justified.
- [ ] Correct architectural layer is selected.
- [ ] Contracts are typed and validated.
- [ ] Provider access goes through the shared Model Gateway.
- [ ] Calls/retries are bounded and failures explicit.
- [ ] Routing and termination are explicit.
- [ ] Required legal verification cannot be bypassed.
- [ ] Unit/workflow/quality tests are added as appropriate.
- [ ] Telemetry is useful and sensitive data is redacted.
- [ ] Relevant architecture notes and ADRs are updated.
