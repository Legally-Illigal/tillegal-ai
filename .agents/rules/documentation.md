# Documentation Rules

## 1. Purpose

These rules define how coding agents create and maintain technical documentation for Tillegal AI Service.

Documentation must describe the actual implementation or clearly identify a proposal. It must not silently turn assumptions into requirements or make undocumented architectural decisions appear approved.

## 2. Documentation Sources

Before writing or modifying documentation:

1. Inspect the relevant existing documentation.
2. Identify the document's purpose and intended audience.
3. Check applicable approved requirements and architecture decisions.
4. Inspect the implementation when documenting current behavior.
5. Preserve existing terminology and structure unless there is a clear reason to change them.

Project requirements and architecture documentation, together with accepted architecture decisions, are authoritative. Engineering guides and coding-harness files complement them; they do not replace them. If a needed source is not present in the repository, identify that gap instead of assuming what it says.

## 3. Separate Facts, Decisions, and Proposals

Clearly distinguish:

- **Confirmed:** explicitly established by an authoritative project source or verified implementation.
- **Implemented:** observable in the current codebase.
- **Proposed:** a recommendation that has not been approved.
- **Assumption:** a temporary premise used because information is missing.
- **Open question:** an unresolved issue requiring clarification or a decision.

Do not describe an ADR with status `Proposed` as an approved decision.

When documentation and implementation disagree, record the discrepancy rather than silently rewriting one to match the other.

## 4. Writing Style

- Use clear, direct, technically precise language.
- Prefer concise explanations over repeated background information.
- Define specialized terms when they are first needed by the intended audience.
- Use consistent names for modules, components, files, configuration keys, and interfaces.
- Prefer active voice and actionable instructions where appropriate.
- Avoid vague claims such as "fully secure," "production-ready," or "highly scalable" without supporting evidence.
- Do not use invented metrics, performance figures, test results, or compliance claims.
- Avoid duplicating large sections of other documents; link to the authoritative source where possible.

Use English for coding-harness rules and agent-facing technical instructions unless the user or an approved project convention specifies another language. Preserve Vietnamese for Vietnamese-language requirements and user-facing content where appropriate.

## 5. File and Markdown Conventions

- Use Markdown for repository documentation unless the project specifies another format.
- Use descriptive headings with a consistent hierarchy.
- Use fenced code blocks with a language identifier when applicable.
- Use relative links for files within the repository where practical.
- Use tables for compact comparisons and lists for sequential or grouped instructions.
- Keep examples consistent with the actual project structure and naming conventions.
- Mark placeholders clearly and never include real credentials.
- Avoid links to nonexistent files, unverified external resources, or paths inferred without checking.

Do not create a new documentation directory or file naming convention when an established one already exists without justification.

## 6. Architecture and API Documentation

When documenting a component, include the relevant details:

- Purpose and responsibility.
- Inputs and outputs.
- Dependencies and boundaries.
- Configuration requirements.
- Failure behavior and recovery expectations.
- Security and data-handling implications.
- Testing and validation approach.
- Related components or documents.

Include only the sections that are relevant to the component. Do not fill sections with speculative content merely to make a template look complete.

For APIs, contracts, configuration keys, and state schemas, use names and types that match the implementation or approved specification.

## 7. Code Changes and Documentation Synchronization

When implementation changes affect documented behavior, review and update the relevant documentation in the same task where practical.

Examples include:

- Public interfaces or schemas.
- Module boundaries and dependency rules.
- Configuration and environment variables.
- Workflow transitions and retry behavior.
- Error handling and fallback behavior.
- Evaluation criteria and test commands.
- Deployment, monitoring, or troubleshooting procedures.

Do not modify unrelated documentation simply to increase the number of changed files.

If a required documentation change depends on an unapproved architectural decision, explain the gap and propose the necessary update rather than asserting that the decision has been finalized.

## 8. Commands and Operational Instructions

Before documenting a command as verified:

- Check that it matches the project's actual tools and scripts.
- Confirm its working directory and required prerequisites.
- Execute it when appropriate and safe.
- Report environmental limitations when it cannot be verified.

Clearly label illustrative commands and placeholders.

Do not invent deployment environments, infrastructure resources, environment variable names, service URLs, or operational procedures.

## 9. Templates and Generated Documents

When using a template:

- Preserve its required fields.
- Replace placeholders only with verified information.
- Mark unknown fields as `TBD`, `Unknown`, or an equivalent explicit status.
- Do not fabricate owners, approval dates, version numbers, evidence, or sign-off.
- Keep status and decision history accurate.

Generated documentation must be reviewed for consistency, broken links, duplicated rules, and claims that are unsupported by the source material.

## 10. Documentation Review Checklist

- [ ] The document has a clear purpose and audience.
- [ ] Claims match authoritative sources or verified implementation.
- [ ] Proposals and assumptions are explicitly labeled.
- [ ] Terminology and filenames are consistent.
- [ ] Examples and commands are accurate or marked illustrative.
- [ ] Links and referenced files exist.
- [ ] No secrets or unnecessary sensitive data are included.
- [ ] Related documents are updated where necessary.
