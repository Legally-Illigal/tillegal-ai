# Implement Task Workflow

## Purpose

Implement a defined engineering task with minimal, focused changes that satisfy its acceptance criteria and preserve the existing architecture.

## When to Use

Use this workflow when implementing a feature, refactoring code, adding infrastructure, or completing a task from the project backlog.

## Inputs

- Task description and acceptance criteria
- Relevant source code and tests
- Applicable `.agents/rules/`
- Relevant `.agents/skills/`
- Approved architecture and requirements documents, when applicable

If essential inputs are missing, identify the gaps before making assumptions.

## Procedure

### 1. Understand the Task

1. Restate the objective and expected outcome.
2. Identify in-scope and out-of-scope changes.
3. Extract acceptance criteria and constraints.
4. Identify dependencies, affected modules, and potential risks.
5. List unresolved questions that could change the implementation.

Do not expand the task into unrelated improvements.

### 2. Inspect the Existing Codebase

1. Inspect relevant files, module boundaries, interfaces, and dependency configuration.
2. Check existing conventions and patterns before introducing new ones.
3. Inspect related tests and documentation.
4. Verify installed dependency versions and existing APIs.
5. Identify whether the task conflicts with approved architecture.

Do not assume that a planned component already exists.

### 3. Plan the Change

Define a concise implementation plan containing:

- Files or modules expected to change
- Main implementation steps
- Required tests
- Configuration or migration impacts
- Risks and unresolved decisions

If the task requires an architectural decision, document the options and request the necessary decision instead of silently committing to one.

### 4. Implement

1. Make the smallest coherent change that satisfies the task.
2. Follow the project's layering, naming, typing, and error-handling conventions.
3. Keep business logic separate from framework and provider-specific details where required by the architecture.
4. Validate external inputs and handle expected failures explicitly.
5. Keep secrets out of source code and logs.
6. Add or update tests alongside the implementation.
7. Update documentation when observable behavior, configuration, interfaces, or architecture changes.

For AI workflows:

- Use the shared Model Gateway rather than introducing an unrelated direct provider integration.
- Use structured outputs and schema validation where the interface requires them.
- Bound retries and graph loops.
- Treat retrieved documents and model outputs as untrusted inputs.
- Do not treat self-reflection as proof of factual correctness.
- For legal functionality, prioritize the validity and traceability of legal sources and citations.

### 5. Verify

Run applicable checks, such as:

- Formatting and linting
- Type or static checks
- Unit tests
- Integration tests, when available and relevant
- Targeted regression tests
- Configuration or startup checks, when relevant

Record commands and actual results. Do not claim a check passed if it was not run or its result is unknown.

If a check cannot run, state the reason and the remaining risk.

### 6. Review the Diff

Check for:

- Changes outside the task scope
- Accidental deletions or unrelated formatting changes
- Missing tests or error handling
- Broken dependency boundaries
- Hard-coded secrets, credentials, or environment-specific values
- Outdated documentation
- Unsupported assumptions

### 7. Report Completion

Provide a concise summary containing:

- What was implemented
- Important files or modules changed
- Tests and checks executed, with actual outcomes
- Known limitations or unresolved issues
- Any required follow-up work

## Guardrails

- Do not change approved architecture without an explicit decision.
- Do not silently redefine acceptance criteria.
- Do not fabricate test results, performance measurements, or implementation details.
- Do not add dependencies without explaining why they are needed.
- Do not remove existing behavior without identifying the impact.
- Do not claim full completion when acceptance criteria remain unmet.

## Definition of Done

- [ ] Acceptance criteria are addressed or explicitly identified as unmet.
- [ ] Implementation follows existing project conventions.
- [ ] Relevant tests are added or updated.
- [ ] Applicable checks are run and results reported.
- [ ] Diff is reviewed for scope and security issues.
- [ ] Documentation is updated where necessary.
- [ ] Remaining risks and limitations are disclosed.