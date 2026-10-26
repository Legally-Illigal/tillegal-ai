# Python Development Skill
---
name: python-development
description: Implement maintainable, typed, testable Python modules and application logic for Tillegal AI Service.
---

## Purpose

Provide a repeatable process for implementing Python functionality consistent with Tillegal AI Service's architecture and coding rules.

## When to Use

- Implementing a Python module or application service.
- Adding data structures or validation.
- Implementing configuration or error handling.
- Refactoring an existing function or module.
- Integrating an existing component through its public interface.

## Procedure

### Step 1: Understand the Change

Read the task, relevant rules, existing implementation, and tests.

Determine:

- Expected behavior.
- Inputs and outputs.
- Dependencies and side effects.
- Expected failure behavior.
- Relevant compatibility requirements.

Clarify blocking ambiguities instead of inventing requirements.

### Step 2: Identify the Correct Module

Place the implementation according to responsibility and approved dependency boundaries.

- Keep reusable framework logic independent of legal-specific behavior.
- Keep provider-specific calls behind the Model Gateway.
- Keep orchestration logic within the approved workflow layer.
- Avoid unrelated persistence, transport, or business logic inside utility modules.

Follow the repository's actual structure rather than creating a parallel structure unnecessarily.

### Step 3: Define Contracts

For public or cross-module interfaces:

- Specify parameter and return types.
- Define required and optional fields.
- Validate untrusted inputs.
- Distinguish missing, invalid, and empty values.
- Define meaningful error behavior.

Use the project's established data-validation conventions.

### Step 4: Implement

- Keep functions and classes focused.
- Prefer explicit dependencies.
- Use asynchronous operations for I/O when required by the runtime.
- Avoid blocking asynchronous execution paths.
- Apply timeouts to remote calls where supported.
- Handle exceptions deliberately.
- Avoid unnecessary abstractions and dependencies.

### Step 5: Test

Add tests for relevant behavior:

- Expected successful results.
- Invalid input.
- Boundary conditions.
- Expected exceptions.
- External dependency failures.
- Important regression cases.

Use mocks or fakes for external systems when testing local logic.

### Step 6: Validate the Change

Run the relevant tests and configured quality checks.

Inspect the diff for:

- Unrelated modifications.
- Dead code and unused imports.
- Incorrect type assumptions.
- Hidden side effects.
- Security and data-handling risks.
- Documentation that no longer matches behavior.

## Design Guidelines

### Types and Validation

Prefer explicit types at stable interfaces. Avoid unnecessary `Any`, unchecked dictionaries, and assumptions about external response formats.

### Error Handling

Catch exceptions only when the implementation can handle them or add useful context. Preserve exception causes and avoid swallowing failures.

### Asynchronous Code

Use `async` and `await` consistently. Do not create unbounded concurrency or introduce arbitrary event-loop management.

### Configuration

Read configuration through the approved mechanism. Do not hardcode environment-specific values or secrets.

## Guardrails

- Do not disable tests, typing, or lint rules to hide defects.
- Do not silently alter public behavior.
- Do not retry all exceptions indiscriminately.
- Do not use `print()` as a substitute for application logging.
- Do not claim unexecuted validation checks passed.

## Expected Output

A focused implementation, relevant tests, updated documentation where needed, and an accurate validation report.

## Completion Checklist

- [ ] Correct module and interface were selected.
- [ ] Inputs, outputs, and failure behavior are explicit.
- [ ] Code follows project conventions.
- [ ] Tests cover the changed behavior.
- [ ] Relevant quality checks were executed.
- [ ] Scope and documentation were reviewed.
