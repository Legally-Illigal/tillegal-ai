# ADR-003: Treat Evaluation as a Versioned Quality Gate

- **Status:** Proposed
- **Date:** 2026-10-26
- **Decision owners:** Tillegal AI Service team

## Context

A legal assistant can produce fluent, plausible text while citing an incorrect, revoked, irrelevant, or unsupported legal provision. Ordinary software tests and language-quality metrics are insufficient to establish legal-answer correctness.

Tillegal therefore needs repeatable evaluation of retrieval, legal-basis accuracy, citation verification, scenario handling, groundedness, and operational behavior.

## Decision

Maintain versioned evaluation datasets and repeatable evaluation procedures. Use evaluation results as a quality gate for material changes to models, prompts, retrieval, workflow logic, citation verification, and response contracts.

The exact metrics, dataset size, acceptance thresholds, and release-blocking policy must be established by the team based on project requirements and reviewed evaluation examples.

## Evaluation Dimensions

### Retrieval Quality

Assess whether the system retrieves relevant, authoritative legal sources and the appropriate legal-document versions.

### Legal-Basis Correctness

Assess whether cited provisions are applicable to the scenario, accurately represented, and valid for the relevant time where temporal applicability matters.

### Citation Verification

Assess whether citations resolve to the intended sources and support the claims associated with them.

### Answer Groundedness

Assess whether factual and legal claims are supported by retrieved evidence and whether uncertainty is communicated when evidence is insufficient.

### Scenario Handling

Assess whether material facts are correctly applied, missing facts are identified, and unsupported conclusions are avoided.

### Operational Quality

Assess latency, failure rates, retries, token usage, and cost where reliable measurements are available.

## Failure Priority

Use the shared project error-severity order:

1. Wrong, inapplicable, revoked, or non-supporting legal basis.
2. Incorrect application of law to the scenario or fabricated material facts.
3. Misleading or incorrect verification status.
4. Missing material caveat, uncertainty, or limitation.
5. Wording, structure, and style issues that do not change legal meaning.

A correct conclusion with an incorrect legal basis must not automatically be treated as a passing answer.

## Dataset and Reproducibility

Each evaluation run should record:

- dataset version and case IDs;
- expected evidence and citations;
- scoring rubric version;
- model provider/profile and prompt version;
- workflow and retrieval configuration versions;
- evaluator version and run timestamp;
- per-case result and failure category;
- reviewed notes and known limitations.

Keep datasets versioned. Separate development/tuning examples from held-out regression cases where feasible. Use synthetic or approved data when possible, and apply appropriate access and retention controls to sensitive examples.

## Role of Self-Reflection

A Self-Reflection node may flag unsupported claims, uncertainty, or insufficient evidence. Its output is diagnostic, not proof of correctness.

Self-assessment must not replace source-level citation verification or reviewed evaluation. A model's confidence in its own answer is not independent evidence that the legal basis is correct.

## Consequences

### Benefits

- Quality changes can be compared across versions.
- Legal-basis and citation regressions can be identified before promotion.
- Failures can be categorized and converted into regression cases.

### Trade-offs

- Datasets and scoring rubrics require maintenance and review.
- Automated metrics may not capture every legal interpretation issue.
- Model-provider changes may introduce variance that needs controlled comparison.

## Validation Before Acceptance

Define:
- ownership of the initial evaluation dataset;
- the review and scoring process;
- baseline metrics;
- release-blocking criteria;
- how disputed or ambiguous cases are handled.

Then run a repeatable baseline against the current implementation.

## Revisit When

The project's quality objectives change, a more appropriate benchmark becomes available, or evaluation repeatedly fails to detect material legal-basis or citation errors.
