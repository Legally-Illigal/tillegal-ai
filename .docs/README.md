# Tillegal AI Service — Engineering Documentation

## 1. Purpose

This directory contains concise engineering documentation for developing, testing, operating, and maintaining the Tillegal AI Service.

These documents are the project's engineering reference for developers and AI coding agents. Keep them aligned with the implementation, configuration, tests, and accepted architecture decisions.

## 2. Documentation Principles

- **No invented requirements:** Do not treat examples, proposals, or unspecified values in these documents as approved decisions.
- **Keep documentation aligned with code:** Update relevant documents when implementation decisions or operational procedures change.
- **Preserve architectural boundaries:** Keep reusable AI framework components separate from Tillegal-specific legal application logic.
- **Prioritize legal correctness:** Legal-basis accuracy and citation verification are critical quality concerns.
- **Make uncertainty explicit:** Do not claim that a source, citation, or legal conclusion has been verified unless the verification process supports that claim.

## 3. Directory Structure

```text
tillegal-ai-docs/
├── README.md
├── architecture/
│   ├── overview.md
│   ├── component-design.md
│   ├── dependency-rules.md
│   ├── runtime-flow.md
│   ├── model-gateway.md
│   ├── evaluation-design.md
│   └── observability-design.md
├── development/
│   ├── setup.md
│   ├── coding-conventions.md
│   ├── testing-guide.md
│   ├── debugging.md
│   └── adding-a-new-agent.md
├── operations/
│   ├── configuration.md
│   ├── deployment.md
│   ├── monitoring.md
│   ├── troubleshooting.md
│   └── incident-response.md
└── decisions/
    ├── ADR-001-langgraph.md
    ├── ADR-002-litellm.md
    ├── ADR-003-evaluation.md
    ├── ADR-004-observability.md
    └── ADR-005-supabase-pgvector.md
```

## 4. Architecture

The `architecture/` directory describes the AI Service's boundaries, components, dependencies, runtime workflow, model access, evaluation, and observability.

| Document | Purpose |
|---|---|
| `architecture/overview.md` | System purpose, scope, boundaries, and architectural principles |
| `architecture/component-design.md` | Responsibilities and interfaces of major components |
| `architecture/dependency-rules.md` | Dependency direction and architectural constraints |
| `architecture/runtime-flow.md` | Request-processing flow and verification stages |
| `architecture/model-gateway.md` | Shared model-access abstraction and provider integration |
| `architecture/evaluation-design.md` | Quality dimensions and evaluation approach |
| `architecture/observability-design.md` | Logging, metrics, tracing, and operational signals |

## 5. Development

The `development/` directory provides practical guidance for working on the codebase.

| Document | Purpose |
|---|---|
| `development/setup.md` | Local environment and project setup |
| `development/coding-conventions.md` | Code organization and implementation conventions |
| `development/testing-guide.md` | Unit, integration, workflow, and evaluation testing |
| `development/debugging.md` | Debugging workflow and evidence collection |
| `development/adding-a-new-agent.md` | Steps and constraints for introducing an agent |

## 6. Operations

The `operations/` directory documents runtime configuration, release procedures, monitoring, troubleshooting, and incident handling.

| Document | Purpose |
|---|---|
| `operations/configuration.md` | Configuration validation, environment separation, and secret management |
| `operations/deployment.md` | Build, test, deployment, smoke testing, and rollback |
| `operations/monitoring.md` | Service, workflow, model gateway, and evaluation signals |
| `operations/troubleshooting.md` | Diagnosis of common operational and workflow failures |
| `operations/incident-response.md` | Incident detection, containment, recovery, and follow-up |

## 7. Architecture Decision Records

The `decisions/` directory records accepted and proposed architectural decisions, their rationale, constraints, alternatives, consequences, and validation requirements.

| ADR | Decision |
|---|---|
| `decisions/ADR-001-langgraph.md` | LangGraph for workflow orchestration |
| `decisions/ADR-002-litellm.md` | LiteLLM behind a Tillegal-owned Model Gateway |
| `decisions/ADR-003-evaluation.md` | Versioned evaluation as a quality gate |
| `decisions/ADR-004-observability.md` | Structured, correlated observability |
| `decisions/ADR-005-supabase-pgvector.md` | Supabase Postgres with pgvector for RAG storage |

**ADR status:** ADR-001, ADR-002, and ADR-005 are accepted. ADR-003 and ADR-004 remain `Proposed`.

When an ADR is accepted, update its status and record any relevant implementation or validation evidence. When a decision is superseded, preserve the historical record and link to the replacement ADR.

## 8. Key Architectural Constraints

### 8.1 Reusable Framework and Application Separation

Keep generic framework capabilities separate from Tillegal-specific legal workflows.

Reusable capabilities may include:
- workflow orchestration;
- model gateway and provider abstraction;
- prompt and context management;
- shared workflow state and contracts;
- evaluation infrastructure;
- logging, metrics, and tracing.

Tillegal-specific modules own legal-domain behavior, including legal-source retrieval, evidence assessment, legal-answer generation, and citation verification.

### 8.2 Model Access

- Agents must use the shared Model Gateway.
- Provider SDKs must not be called directly from application agents.
- Model routing, retries, timeouts, and fallback must be controlled and bounded.
- Validate outputs before passing them to downstream workflow stages.
- Do not fabricate token usage or cost data.

### 8.3 Workflow Reliability

- Define explicit state and node contracts.
- Bound loops, retries, and execution time.
- Record workflow outcomes and stop reasons.
- Treat retrieved content as untrusted input.
- Do not allow fallback or self-reflection to bypass required verification.

### 8.4 Legal Quality

- Prioritize correct and applicable legal bases and reliable citations.
- Do not treat a plausible conclusion as sufficient when its legal basis is incorrect.
- State uncertainty when evidence is insufficient.
- Treat self-reflection as a diagnostic mechanism, not proof of correctness.
- Use versioned evaluation cases to detect regressions.

### 8.5 Security and Observability

- Never log secrets or credentials.
- Do not log complete prompts, answers, or legal documents by default.
- Use correlation identifiers to trace workflow execution.
- Restrict and minimize sensitive data collected for debugging or evaluation.
- Keep telemetry implementation details out of domain business logic where practical.

## 9. Change Management

When making a material implementation change:

1. Review the relevant approved requirements and architecture documents.
2. Identify the affected architecture, development, operations, and ADR documents.
3. Implement and test the change.
4. Run relevant evaluation cases when model behavior, retrieval, prompts, workflows, or verification are affected.
5. Update documentation to match the verified implementation.
6. Create or update an ADR if the architectural decision changes.
7. Record unresolved assumptions and decisions explicitly.

Do not silently change approved project decisions through implementation notes. Record durable architecture changes in the relevant ADR and follow the project's review process.

## 10. Guidance for AI Coding Agents

AI coding agents working in this repository must:

- Read the relevant architecture and development documents before making structural changes.
- Follow accepted project decisions when they conflict with informal examples or proposed ADRs.
- Inspect the existing code before assuming a component, interface, or dependency exists.
- Avoid introducing new frameworks or infrastructure without justification.
- Preserve dependency direction and component boundaries.
- Avoid unrelated refactoring.
- Add tests for new behavior and failure paths.
- Never claim tests, evaluations, or deployments passed unless they were actually run and verified.
- Update relevant documentation when implementation behavior changes.
- Ask for clarification when a required architectural decision is unresolved and cannot safely be inferred.

## 11. Document Maintenance

These documents should remain concise and implementation-oriented. Keep implementation guidance in sync with the code and avoid duplicating content unnecessarily.

Review the documentation when:
- a component or interface changes;
- a workflow stage is added, removed, or reordered;
- a model provider or gateway implementation changes;
- evaluation methodology or acceptance criteria change;
- deployment or operational procedures change;
- an ADR is accepted, rejected, or superseded.

Keep document paths and cross-references valid as the repository evolves.
