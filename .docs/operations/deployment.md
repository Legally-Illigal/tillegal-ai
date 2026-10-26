# Deployment

## 1. Purpose

This document describes a repeatable deployment process for the Tillegal AI Service. The service should remain independently buildable and deployable while respecting its integration contracts with the Backend and other system components.

Environment-specific deployment details must be maintained alongside the actual deployment configuration.

## 2. Deployment Principles

- Build artifacts from reviewed source revisions.
- Keep credentials and environment configuration outside the application image.
- Pin dependencies and maintain a reproducible dependency lock file.
- Run automated tests before promoting an artifact.
- Evaluate changes that may affect legal-answer quality.
- Keep a known-good artifact and configuration available for rollback.
- Avoid introducing distributed infrastructure unless required by the approved architecture and workload.

## 3. Deployment Pipeline

### Step 1 — Validate

Run applicable formatting, linting, type checking, static checks, and unit tests.

### Step 2 — Build

Build the application artifact or container image from the reviewed commit. Record the commit identifier and artifact version.

### Step 3 — Test

Run automated tests, including:
- unit tests for agents and workflow nodes;
- workflow transition and failure-path tests;
- Model Gateway contract tests;
- integration tests using mocked external services where practical.

Live provider tests should be controlled to avoid unnecessary cost and dependency on external availability.

### Step 4 — Evaluate

Run the evaluation cases relevant to the change. Model, prompt, retrieval, workflow, and verification changes may affect legal correctness even when ordinary unit tests pass.

### Step 5 — Deploy to a Test Environment

Apply environment-specific configuration and secrets through the approved deployment mechanism. Verify health and dependency connectivity.

### Step 6 — Smoke Test

Check:
- service startup and readiness;
- API contract validity;
- model gateway operation;
- retrieval behavior where applicable;
- citation-verification behavior;
- error handling and timeout behavior.

### Step 7 — Promote

Promote the same tested artifact to the next environment rather than rebuilding from an unverified source state.

### Step 8 — Observe

Monitor errors, latency, provider failures, fallback usage, workflow stop reasons, and token/cost information where available.

## 4. Runtime Requirements

The deployed service should provide:

- health/readiness checks appropriate to its dependencies;
- bounded request and model-call timeouts;
- bounded retries and workflow execution;
- graceful shutdown behavior;
- structured logs with request correlation;
- configurable concurrency and resource limits;
- secure handling of secrets and user-provided content.

Do not assume the service can handle unlimited concurrent model calls. Concurrency limits must account for provider quotas, application resources, and expected workload.

## 5. Release Record

Record the following for each release:

- source commit and artifact identifier;
- application and workflow versions;
- prompt/model profile versions where applicable;
- relevant evaluation dataset and results;
- configuration changes, excluding secret values;
- known limitations;
- rollback artifact and procedure.

## 6. Rollback

Consider rollback when a release causes material service instability, invalid response contracts, a significant legal-basis or citation regression, a security issue, or uncontrolled provider usage.

1. Stop further promotion.
2. Restore the previous known-good artifact and compatible configuration.
3. Verify health and run smoke tests.
4. Run relevant quality checks, especially for legal-answer regressions.
5. Preserve incident evidence with sensitive data redacted.
6. Record the cause or investigation status.

Rollback does not remove the need to investigate incorrect answers that may already have been returned.

## 7. Related Documents

- `../development/setup.md`
- `../development/testing-guide.md`
- `monitoring.md`
- `troubleshooting.md`
- `incident-response.md`
