# Prompt Engineering Skill
---
name: prompt-engineering
description: Design, structure, version, and evaluate prompts for Tillegal AI Service while preserving explicit contracts and security boundaries.
---

## Purpose

Develop prompts that produce useful, structured, and appropriately constrained model outputs.

Prompt design must work alongside deterministic validation, retrieval, application policies, and evaluation. A prompt is not a substitute for these controls.

## When to Use

- Creating or revising a system or task prompt.
- Defining agent instructions.
- Improving structured-output compliance.
- Reducing unsupported claims.
- Designing reflection or judging prompts.
- Improving prompts for legal question answering or citation-related tasks.

## Procedure

### Step 1: Define the Objective

Identify:

- The task the model must perform.
- The intended input.
- The expected output.
- The constraints the model must follow.
- The failure conditions.
- The downstream component that consumes the result.

Do not combine unrelated responsibilities into one prompt without justification.

### Step 2: Define the Contract

Specify the required output format and fields when structured output is needed.

Clarify:

- Required versus optional fields.
- Allowed values and types.
- How missing information is represented.
- How uncertainty is communicated.
- What to do when evidence is insufficient.
- Which conditions require a failure or clarification result.

Enforce critical contracts through application-side validation rather than prompt wording alone.

### Step 3: Separate Instructions from Data

Keep system-level instructions separate from user-provided input and retrieved content.

- Treat retrieved documents and user content as untrusted data.
- Do not allow instructions embedded in retrieved material to override application policies.
- Define which sources may support factual claims.
- Avoid inserting unnecessary personal or confidential information.
- Do not place secrets in prompts.

### Step 4: Make Reasoning Requirements Explicit

Specify the task's evidence requirements, decision criteria, and expected explanation style.

For legal-domain prompts, where required:

- Distinguish facts supplied by the user from assumptions.
- Identify missing facts that could change the analysis.
- Require legal claims to be tied to relevant source evidence.
- Avoid presenting unsupported conclusions as certain.
- Distinguish source retrieval from source verification.
- Preserve citation identifiers or provenance required by downstream validation.

Do not rely on a generic instruction to "be accurate" as the only quality control.

### Step 5: Version and Maintain Prompts

Use the repository's established prompt storage and versioning approach.

When changing a prompt:

- Record the purpose of the change.
- Identify affected workflows.
- Preserve backward compatibility where required.
- Avoid duplicating shared policies unnecessarily.
- Update relevant tests and evaluations.

Do not introduce a prompt registry or templating dependency unless justified by the architecture.

### Step 6: Evaluate the Change

Use representative examples, including difficult and negative cases.

Check:

- Output schema compliance.
- Task completion.
- Unsupported assertions.
- Missing required fields.
- Appropriate uncertainty.
- Robustness to irrelevant or adversarial input.
- Regression in existing expected behavior.

For legal prompts, assess legal-basis and citation correctness independently of style and fluency.

### Step 7: Review Security and Observability

Confirm that prompt inputs do not expose unnecessary sensitive data and that logs do not capture prompt contents by default without an approved policy.

Use correlation IDs and prompt-version identifiers where supported.

## Reflection and Judge Prompts

Judge prompts should use explicit criteria and return a structured assessment where appropriate.

They must not be treated as definitive proof of correctness. For legal citations, independent source-based verification remains necessary wherever the system is expected to provide verified citations.

## Guardrails

- Do not treat prompt wording as an authorization boundary.
- Do not assume JSON-like output is valid JSON or conforms to a schema.
- Do not use a single favorable example as evidence of quality.
- Do not claim improved performance without comparative evaluation.
- Do not silently change shared instructions in ways that affect unrelated agents.

## Expected Output

A prompt or prompt revision, its input/output contract, relevant tests or evaluation cases, and a record of important behavioral changes.

## Completion Checklist

- [ ] The prompt has one clear objective.
- [ ] Inputs and outputs are explicit.
- [ ] Untrusted content is separated from instructions.
- [ ] Missing information and uncertainty are handled.
- [ ] Application-side validation is present where needed.
- [ ] Representative evaluations were performed or their absence documented.
