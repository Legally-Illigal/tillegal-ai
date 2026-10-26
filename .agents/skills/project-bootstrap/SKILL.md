# Project Bootstrap Skill
---
name: project-bootstrap
description: Initialize or extend the Tillegal AI Service project foundation while preserving approved architecture and repository conventions.
---

## Purpose

Use this skill when initializing the AI Service repository, establishing foundational modules, or configuring a new development capability.

The objective is to create a working, maintainable foundation without prematurely implementing application features or introducing unapproved architecture.

## When to Use

- Initializing the Python project.
- Establishing the source and test directory structure.
- Configuring dependency management and development tooling.
- Setting up application configuration and startup validation.
- Establishing logging, error handling, and basic health checks when required.
- Preparing the project for LangGraph and Model Gateway integration.

## Procedure

### Step 1: Discover the Repository

Inspect:

- Existing files and directory structure.
- Python version requirements.
- Dependency manager and lockfiles.
- Current application entry points.
- Test, formatting, linting, and type-checking configuration.
- Approved architecture documentation and ADRs.

Do not overwrite existing project configuration before understanding its purpose.

### Step 2: Confirm the Required Foundation

Derive the required structure from approved documentation and existing conventions.

Consider the following concerns only when required:

- Application entry point and runtime configuration.
- Core domain or application contracts.
- Agent and workflow modules.
- Model Gateway abstraction.
- Provider integration.
- Evaluation and observability interfaces.
- Unit and integration test organization.

Do not create every possible module merely because it appears in a proposed architecture.

### Step 3: Establish Project Configuration

- Define project metadata and supported Python versions according to approved requirements.
- Use the existing dependency-management approach.
- Add only necessary dependencies.
- Configure the established formatter, linter, type checker, and test runner when required.
- Separate development dependencies from runtime dependencies where supported.
- Keep credentials out of committed files.
- Provide placeholder-based example configuration when useful.

Do not invent version constraints or upgrade unrelated dependencies without justification.

### Step 4: Establish Basic Runtime Behavior

Where required by the task:

- Implement configuration loading and validation.
- Establish consistent error handling.
- Configure application logging.
- Add a minimal startup or health-check mechanism.
- Ensure startup failures are understandable and do not expose secrets.
- Keep infrastructure initialization separate from business logic.

Do not implement a full API, graph workflow, database, or deployment platform unless the task requires it.

### Step 5: Establish Testing

Create a minimal test structure that matches the selected test framework.

Verify:

- Project modules can be imported.
- Configuration validation behaves as expected.
- The application starts or initializes as intended.
- Basic tests run using the documented command.

Avoid requiring live model-provider credentials for bootstrap tests.

### Step 6: Validate and Document

Run the applicable installation, test, lint, formatting, and type-check commands.

Document:

- Prerequisites.
- Setup and test commands.
- Configuration requirements.
- Current entry points.
- Known limitations.

Only report commands that were actually executed as verified.

## Guardrails

- Do not replace an established architecture without authorization.
- Do not add speculative abstractions or infrastructure.
- Do not commit real secrets.
- Do not create duplicate configuration mechanisms.
- Do not claim production readiness based on a successful initial build.

## Expected Output

A minimal, runnable project foundation, relevant tests, necessary configuration, and setup documentation.

## Completion Checklist

- [ ] Existing repository conventions were inspected.
- [ ] Required project structure is in place.
- [ ] Dependencies and configuration are justified.
- [ ] Secrets are not embedded in source code.
- [ ] Basic initialization and tests work, or blockers are documented.
- [ ] Setup instructions reflect the actual implementation.
