# Python Coding Conventions

## 1. Purpose

These rules define Python coding conventions for Tillegal AI Service.

Before applying them, inspect the repository for its Python version, dependency manager, formatter, linter, type checker, and existing conventions. Follow established project configuration unless an approved change says otherwise.

Do not invent tool versions or assume that a particular tool is installed.

## 2. General Principles

- Prefer readable, explicit, maintainable code over clever implementations.
- Follow PEP 8 and applicable PEP 257 documentation conventions.
- Use descriptive names that communicate intent.
- Keep functions and classes focused on one responsibility.
- Avoid unnecessary abstraction, duplication, and hidden side effects.
- Prefer standard-library functionality when it meets the requirement.
- Avoid premature optimization.
- Preserve existing public behavior unless a change explicitly requires otherwise.

Use the project's configured formatter and linter instead of introducing conflicting formatting rules.

## 3. Type Annotations

- Add type annotations to public functions, methods, and important data structures.
- Prefer explicit parameter and return types.
- Use suitable types from `typing` or the standard library when they improve clarity.
- Represent optional values explicitly.
- Avoid `Any` when a meaningful type can be defined.
- Do not use type suppression comments merely to bypass a problem without understanding it.

Use a project's existing typed data-contract approach where one exists. Do not introduce a second schema framework unnecessarily.

## 4. Functions and Classes

- Keep functions small enough to understand and test.
- Avoid functions that mix orchestration, model invocation, data transformation, persistence, and logging without a clear reason.
- Prefer explicit dependencies over hidden global dependencies.
- Use classes when they represent meaningful state, behavior, or a required interface; do not create classes solely to wrap a single trivial function.
- Avoid mutable default arguments.
- Avoid broad exception handling that hides the original failure.
- Do not return ambiguous sentinel values when an explicit result or exception is more appropriate.

## 5. Data and Contracts

- Use explicit data structures for important module boundaries.
- Validate external inputs and untrusted outputs.
- Distinguish missing values, invalid values, and legitimate empty results.
- Avoid passing unstructured dictionaries through the entire system when a stable contract is needed.
- Keep serialization and deserialization behavior explicit.
- Do not assume that a model-generated response conforms to its requested schema.

Choose Pydantic models, dataclasses, TypedDict, or other structures according to the existing architecture and the specific contract. Do not introduce multiple competing approaches without a reason.

## 6. Asynchronous Programming

- Use `async` and `await` consistently for asynchronous I/O.
- Do not block the event loop with synchronous network or filesystem operations in asynchronous request paths.
- Use asynchronous libraries where required by the runtime and supported by the existing dependencies.
- Do not create unbounded concurrent tasks.
- Bound concurrency when calling external model providers or other remote services.
- Handle cancellation and timeouts according to the execution context.
- Do not call `asyncio.run()` inside an already running event loop.

Use synchronous code when it is appropriate and compatible with the caller; do not make every function asynchronous by default.

## 7. Exceptions and Resource Management

- Catch exceptions only when the code can handle them, translate them meaningfully, or add useful context.
- Preserve exception causes when raising a replacement exception.
- Avoid bare `except` clauses.
- Avoid silently swallowing failures.
- Use context managers for resources that require deterministic cleanup.
- Apply explicit timeouts to external calls where supported.
- Distinguish retryable failures from permanent failures.

Do not retry every exception indiscriminately.

## 8. Configuration and Dependencies

- Load configuration through the repository's approved configuration mechanism.
- Validate required configuration at startup or at the appropriate initialization boundary.
- Keep secrets out of source code and default configuration files.
- Pin or constrain dependencies according to the project's dependency-management policy.
- Do not add a package without a clear need.
- Do not upgrade unrelated dependencies as part of a feature task.
- Keep provider-specific SDK usage behind the approved Model Gateway.

## 9. Logging and Instrumentation

- Use the project's configured logging system rather than ad hoc `print()` calls in application code.
- Include relevant execution or correlation identifiers where available.
- Log meaningful lifecycle events and failures.
- Avoid logging credentials, authorization headers, API keys, or unnecessary user content.
- Do not record full prompts and model responses by default unless an approved, privacy-aware policy explicitly permits it.
- Record timing, token usage, and cost only when the relevant data is available and the implementation supports it.
- Do not fabricate usage or cost values when provider metadata is missing.

## 10. Testing and Maintainability

- Write tests for behavior, not private implementation details unless there is a specific reason.
- Keep tests deterministic and isolated.
- Mock external services at appropriate boundaries.
- Avoid real provider calls in ordinary unit tests.
- Use explicit fixtures and test data.
- Remove dead code and unused imports introduced by the change.
- Avoid disabling type checks, lint rules, or tests to hide defects.

## 11. Documentation

Public classes, functions, and non-obvious behavior should have useful documentation.

Document assumptions, side effects, failure modes, and important constraints. Do not write comments that merely repeat the code.

Use the repository's established docstring style and language conventions.

## 12. Completion Checklist

- [ ] Code follows existing project conventions.
- [ ] Important interfaces have type annotations.
- [ ] Inputs and external outputs are validated.
- [ ] Exceptions and timeouts are handled appropriately.
- [ ] Async operations do not introduce unintended blocking.
- [ ] No secrets or sensitive data are exposed.
- [ ] Relevant tests and configured quality checks have been run.
