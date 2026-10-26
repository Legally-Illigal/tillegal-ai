# Evaluation Design

> Evaluation must distinguish legal correctness from fluent language and generic model quality.

## 1. Purpose and priority

Evaluation supports regression testing, comparison of model/workflow configurations, diagnosis of failure modes and evidence-based technology choices. The highest priority is the correctness of legal grounds and citations. A plausible conclusion with an incorrect/revoked/non-supporting legal basis is a failure.

Establish an initial baseline, then refine quantitative thresholds using measured results. Do not invent acceptance thresholds before a baseline is agreed.

## 2. Evaluation layers

### A. Contract and workflow correctness
- Input/output schema validity.
- State transitions and routing.
- Correct termination and `stop_reason`.
- Bounded loops/retries and budget enforcement.
- Error-path behavior and fallback behavior.

### B. Retrieval and evidence
- Whether relevant legal sources/passages are retrieved.
- Whether evidence contains source/document/version/location metadata.
- Whether material issues, exceptions or conflicting sources are missed.
- Whether the system distinguishes missing evidence from evidence disproving a claim.

### C. Answer and legal reasoning
- Correctness of legal rule and its application to user-provided facts.
- Whether assumptions are incorrectly presented as facts.
- Whether material missing facts trigger clarification or a stated limitation.
- Whether the answer remains grounded in the retrieved evidence.

### D. Citation verification
Evaluate separately:
- Citation identifier and location correctness.
- Source existence and retrievability.
- Whether the cited text actually supports the linked claim.
- Legal version/effectiveness/temporal applicability when metadata is available.
- Correct handling of `VERIFIED`, `UNVERIFIED`, `INCORRECT` and `UNREACHABLE`.

### E. Operational quality
- End-to-end and per-node latency.
- Model-call count, token usage and cost per request.
- Provider errors, fallback frequency and workflow termination causes.
- Stability across repeated runs where stochastic behavior is relevant.

## 3. Error severity

Use this priority when triaging failures:
1. Wrong, inapplicable, revoked, or non-supporting legal basis.
2. Incorrect application of law to the scenario or fabricated material facts.
3. Misleading or incorrect verification status.
4. Missing material caveat, uncertainty, or limitation.
5. Wording, structure, and style issues that do not change legal meaning.

A single aggregate score must not hide a critical legal/citation failure. Report critical dimensions separately.

## 4. Test data and reproducibility

Each evaluation case should include, as appropriate:
- Stable case ID and task type (Q&A, advice/explanation, citation verification).
- Input question/scenario and relevant conversation context.
- Reference legal issue and expected evidence/citations.
- Expected behavior for missing/ambiguous facts.
- Known legal time/as-of date when relevant.
- Labels/rationale and reviewer provenance.
- Dataset version.

Each run should record:
- Dataset version.
- Workflow/graph version.
- Prompt version.
- Model profile and actual provider/model.
- Retrieval/index/corpus version when available.
- Evaluation code/config version.
- Timestamp, result, latency, usage/cost and failure categories.

Separate development/tuning cases from held-out evaluation cases where practical to reduce overfitting and overly optimistic results.

## 5. Self-Reflection and groundedness

Self-Reflection may be used as a diagnostic or repair signal, not as proof that the answer is correct. A model's own statement that its answer is grounded does not replace source-based checks.

A groundedness check should, where applicable:
1. Split the draft into claims or inspect claim-level units.
2. Link each claim to one or more evidence IDs/citations.
3. Assess whether the evidence supports the claim.
4. Identify unsupported, contradicted or uncheckable claims.
5. Route repairable issues to targeted retrieval/verification within budget.
6. Preserve unresolved status if repair fails.

Use deterministic checks for IDs, schema, source references and metadata wherever possible. LLM-based judgments should be evaluated against labeled examples and reported separately from deterministic checks.

## 6. Evaluation output

Produce machine-readable results suitable for comparing runs. Include per-case outcomes and failure labels, not only a summary score. Summaries should show:
- Counts and rates by task type.
- Legal-basis/citation failure counts.
- Unsupported-claim and insufficient-evidence behavior.
- Verification status confusion/error patterns when labeled data allows.
- Latency distribution and cost/usage summaries.
- Provider/fallback failures.
- Changes against a recorded baseline.

## 7. MVP boundaries

Start with a small, curated regression set and repeatable manual/automated evaluation. Expand the dataset as real failure modes are discovered. Do not claim production-grade legal accuracy solely from a successful demo or a small test set.
