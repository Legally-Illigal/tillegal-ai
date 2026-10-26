# Documentation Skill
---
name: documentation
description: Create, update, and validate technical documentation for Tillegal AI Service using approved requirements and verified implementation.
---

## Purpose

Provide a systematic process for producing accurate, maintainable, and traceable documentation for Tillegal AI Service.

Documentation should help developers understand the system without duplicating authoritative requirements or inventing implementation details.

## When to Use

- Creating a technical document.
- Updating architecture or development documentation.
- Documenting a new module, agent, or workflow.
- Writing configuration or operational instructions.
- Creating or updating an ADR.
- Synchronizing documentation with code changes.
- Reviewing documentation for consistency.

## Procedure

### Step 1: Identify the Document

Determine:

- Purpose and intended audience.
- Required scope and level of detail.
- Existing document structure and naming conventions.
- Relevant authoritative sources.
- Related documents that may require updates.

Reuse existing files when appropriate instead of creating duplicates.

### Step 2: Gather Evidence

Inspect the relevant sources:

- Approved requirements and architecture documentation.
- Approved ADRs and their current status.
- Actual source code and configuration.
- Tests and execution results.
- Existing development and operations guides.

Use the source appropriate to the claim. For example, source code can demonstrate implemented behavior but does not automatically establish that the behavior is an approved requirement.

### Step 3: Establish an Outline

Choose sections that serve the document's purpose.

Depending on the document, relevant sections may include:

- Purpose and scope.
- Responsibilities and boundaries.
- Inputs, outputs, and interfaces.
- Dependencies.
- Configuration.
- Execution flow.
- Error handling.
- Security considerations.
- Testing and validation.
- Limitations and related documents.

Do not include irrelevant sections merely to satisfy a generic template.

### Step 4: Write the Content

- Use precise and direct language.
- Maintain consistent terminology.
- Prefer actionable instructions for development guides.
- Use code examples that match the actual implementation.
- Use diagrams when they materially improve understanding.
- Reference authoritative documents instead of duplicating substantial content.
- Mark unresolved information explicitly.

Distinguish confirmed requirements, implemented behavior, proposals, assumptions, and open questions.

### Step 5: Document Architecture Decisions

When documenting an architectural decision:

- Explain the context and problem.
- Describe the decision or proposed decision.
- Record alternatives when relevant.
- Explain consequences and trade-offs.
- Identify validation and migration needs.
- Preserve the actual approval status.

Do not mark a decision approved unless the appropriate authority has approved it.

### Step 6: Validate Technical Details

Where relevant, verify:

- File paths and module names.
- Public interfaces and data schemas.
- Configuration keys and defaults.
- Dependency names and versions.
- Commands and prerequisites.
- Test results.
- Links and cross-references.

Execute commands when appropriate and safe. If a command cannot be verified, label it accordingly instead of presenting it as tested.

### Step 7: Check Consistency

Review the document against related sources.

Look for:

- Contradictory statements.
- Duplicate or conflicting rules.
- Unsupported claims.
- Incorrect status labels.
- Stale configuration or commands.
- References to nonexistent files.
- Sensitive information in examples.

If sources conflict, record the discrepancy and identify the required resolution. Do not silently rewrite authoritative requirements.

### Step 8: Report the Changes

Summarize:

- Documents created or updated.
- Main topics covered.
- References verified.
- Information still missing.
- Follow-up changes needed.

## Coding Harness Documentation

When creating documentation under `.agents/`:

- Keep rules, agent roles, skills, workflows, and templates distinct.
- Put general mandatory constraints in the appropriate rules file.
- Put role-specific responsibilities in agent definitions.
- Put reusable technical procedures in skills.
- Put task sequences and decision points in workflows.
- Put reusable document structures in templates.
- Avoid copying entire rules into multiple files.
- Do not assume that the target coding tool automatically discovers every file.

## Guardrails

- Do not invent architecture, requirements, approvals, or test outcomes.
- Do not document proposed behavior as implemented.
- Do not change code when the task only requests documentation.
- Do not overwrite authoritative documents without authorization.
- Do not include real secrets or unnecessary personal data.
- Do not claim links, commands, or files were verified unless they were checked.

## Expected Output

Complete Markdown documentation consistent with authoritative project sources, accurate references, clearly marked unresolved details, and a concise change summary.

## Completion Checklist

- [ ] Purpose, audience, and scope are clear.
- [ ] Claims are supported by authoritative sources or verified implementation.
- [ ] Proposals and assumptions are labeled.
- [ ] Examples and commands are accurate or marked illustrative.
- [ ] Related documentation is consistent.
- [ ] Links and file references have been checked.
- [ ] No secrets or unnecessary sensitive data are included.
