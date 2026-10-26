# Release Checklist Workflow

## Purpose

Verify that a proposed release has adequate implementation quality, test evidence, configuration, documentation, and operational readiness.

## When to Use

Use this checklist before creating a release, deploying a build to a shared demo environment, or handing a version over for team evaluation.

This checklist supports release decisions; it does not itself authorize deployment or replace the team's release approval process.

## 1. Scope and Requirements

- [ ] Release scope and included changes are documented.
- [ ] Relevant task acceptance criteria have been reviewed.
- [ ] Known deviations and incomplete items are listed.
- [ ] Changes are consistent with approved architecture and requirements.
- [ ] Required architecture decisions have been approved or explicitly identified as pending.
- [ ] No unrelated or unreviewed changes are included.

## 2. Code Quality

- [ ] Code review has been completed.
- [ ] Formatting and linting checks have been run where configured.
- [ ] Type checking or static analysis has been run where configured.
- [ ] No known blocker or major defect remains without an explicit release decision.
- [ ] Dependencies and dependency changes have been reviewed.
- [ ] Configuration defaults are appropriate for the target environment.

## 3. Testing and Evaluation

- [ ] Relevant unit tests have been run.
- [ ] Relevant integration tests have been run, where available.
- [ ] Regression tests have been run for affected behavior.
- [ ] Application startup and health checks have been verified where applicable.
- [ ] Failed, skipped, or unavailable tests are documented.
- [ ] Test results reflect actual execution rather than assumptions.

For AI Service changes:

- [ ] Structured output and schema validation have been tested where applicable.
- [ ] Model Gateway error handling and timeout behavior have been checked.
- [ ] Retry, fallback, and graph termination behavior are bounded.
- [ ] Representative AI evaluation cases have been executed where required.
- [ ] Token usage, latency, and cost instrumentation have been checked where applicable.

For legal functionality:

- [ ] Evaluation includes legal-source and citation correctness.
- [ ] Relevant tests cover unsupported claims and missing facts.
- [ ] Legal-source version or validity checks are included where supported by the implementation.
- [ ] A plausible answer with an incorrect legal basis is treated as a failure.

Do not use a single aggregate quality score to conceal critical citation or legal-grounding failures.

## 4. Security and Privacy

- [ ] No secrets or credentials are committed to source control.
- [ ] Environment-specific credentials are configured through the approved secret mechanism.
- [ ] Logs do not expose credentials or unnecessary sensitive content.
- [ ] Input validation and relevant access controls have been checked.
- [ ] Error responses do not reveal unnecessary internal details.
- [ ] External model or provider calls comply with the project's approved data-handling configuration.
- [ ] Dependencies and known security concerns have been reviewed where tooling is available.

## 5. Configuration and Deployment

- [ ] Required environment variables are documented.
- [ ] Required services and dependencies are available.
- [ ] Database migrations or schema changes have been reviewed and tested, where applicable.
- [ ] Startup commands and container configuration have been verified, where applicable.
- [ ] Health checks and readiness behavior are appropriate for the target environment.
- [ ] Resource requirements and operational limitations are documented.
- [ ] Rollback or recovery steps are defined for changes that could affect existing data or service availability.

Do not deploy to a shared environment without the required authorization.

## 6. Observability and Operations

- [ ] Relevant errors are logged with sufficient diagnostic context.
- [ ] Logs exclude secrets and unnecessary sensitive payloads.
- [ ] Relevant latency and failure metrics are available where implemented.
- [ ] AI token usage and cost are tracked when the underlying provider exposes sufficient data.
- [ ] External dependency failures can be diagnosed.
- [ ] Known monitoring or alerting gaps are documented.

## 7. Documentation and Versioning

- [ ] User-facing or API behavior changes are documented.
- [ ] Configuration and setup instructions are current.
- [ ] Relevant architecture documents and decision records are updated.
- [ ] Release notes summarize notable changes and known limitations.
- [ ] Version identifiers and build artifacts are traceable to the source revision.
- [ ] No document claims a capability that has not been implemented or verified.

## 8. Release Decision

Record one of the following:

- **Ready:** Required checks are complete, and no unresolved issue blocks release.
- **Ready with accepted limitations:** Known gaps are documented and explicitly accepted by the responsible team.
- **Not ready:** Required checks are missing or a blocking issue remains.

Record:

- Release/version identifier
- Source revision or commit
- Environment
- Checks performed and results
- Known issues and accepted risks
- Decision and responsible approver, according to the team's process

## Guardrails

- Do not mark an unchecked item as complete.
- Do not invent build, test, security, or deployment results.
- Do not equate a successful build with production readiness.
- Do not suppress critical AI evaluation failures behind average scores.
- Do not treat this checklist as a substitute for explicit release authorization.

## Definition of Done

- [ ] All applicable checklist items have been assessed.
- [ ] Unavailable checks and unresolved risks are documented.
- [ ] Release artifacts are traceable to a source revision.
- [ ] The release decision is explicit.
- [ ] Required team approval has been obtained before deployment.