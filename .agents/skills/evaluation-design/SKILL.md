# Evaluation Design Skill
---
name: evaluation-design
description: Design reproducible evaluation datasets, metrics, test cases, and quality gates for Tillegal AI Service.
---

## Purpose

Design evaluation methods that measure whether Tillegal AI Service behaves as intended.

Evaluation must distinguish deterministic functional correctness from model-dependent quality and must prioritize legal-source correctness for legal use cases.

## When to Use

- Creating an evaluation dataset.
- Defining metrics or acceptance criteria.
- Evaluating a new model, prompt, agent, or workflow.
- Comparing model or prompt versions.
- Establishing regression evaluations.
- Investigating quality degradation.

## Procedure

### Step 1: Define the Evaluation Objective

Specify:

- The behavior or risk being evaluated.
- The component under evaluation.
- The expected input and output.
- The available reference evidence.
- The evaluation method.
- The intended decision supported by the results.

Do not choose metrics merely because a library makes them available.

### Step 2: Separate Evaluation Layers

Consider distinct evaluation layers where relevant:

1. **Functional correctness:** schemas, routing, validation, error handling, and deterministic behavior.
2. **Retrieval quality:** whether relevant source material is retrieved.
3. **Citation quality:** whether citations exist and support the claims they accompany.
4. **Legal reasoning quality:** whether the answer applies relevant law to the stated facts.
5. **Response quality:** clarity, completeness, and appropriate communication of uncertainty.
6. **Operational quality:** latency, failure rate, and resource usage.

Keep the measurements separate when combining them would hide an important failure.

### Step 3: Build the Dataset

Use representative cases based on approved requirements and available authoritative evidence.

Include relevant categories such as:

- Straightforward questions.
- Questions with missing facts.
- Ambiguous or underspecified scenarios.
- Questions involving multiple legal provisions.
- Incorrect or unsupported citations.
- Revoked, amended, or temporally inapplicable provisions when the source data supports these distinctions.
- No-result and insufficient-evidence cases.
- Adversarial or irrelevant input.

Record the expected outcome, supporting evidence, evaluation criteria, and known limitations for each case.

Do not fabricate gold-standard legal answers or treat unreviewed model output as authoritative ground truth.

### Step 4: Define Metrics

Choose metrics that map to the evaluation objective.

Possible measures include:

- Schema validity rate.
- Task completion rate.
- Retrieval precision and recall where reference judgments exist.
- Citation existence and claim-support accuracy.
- Legal-basis applicability accuracy.
- Unsupported-claim rate.
- Appropriate uncertainty rate.
- Latency and failure rate.
- Token usage and cost where actual metadata is available.

Define each metric's numerator, denominator, aggregation method, and failure interpretation.

Do not claim a metric is meaningful without considering the quality of its reference labels.

### Step 5: Set Acceptance Criteria

Use thresholds from approved requirements or established project decisions.

If no threshold exists:

- Report the baseline and observed results.
- Explain the risk being controlled.
- Propose a threshold for review if useful.
- Label the proposal as unapproved.

For legal functionality, do not let a strong average score hide critical errors in legal grounds or citations. Consider explicit critical-failure reporting or gating where approved.

### Step 6: Run Reproducible Evaluations

Record relevant metadata where available:

- Dataset version.
- Model and provider.
- Prompt version.
- Workflow or code version.
- Evaluation configuration.
- Execution date.
- Metric definitions.
- Results and known limitations.

Use a consistent comparison method when evaluating changes. Separate random variation from genuine improvement where feasible.

### Step 7: Analyze Results

Inspect aggregate metrics and individual failures.

Classify failures by cause, such as retrieval, citation validation, scenario interpretation, output formatting, or provider failure.

Do not report only a summary score when a small number of critical failures materially affect safety or correctness.

## Legal AI Priority

Legal-basis and citation correctness are critical dimensions.

A correct final conclusion does not compensate for a materially incorrect legal basis. LLM-as-a-judge and Self-Reflection scores should be treated as supporting signals, not definitive legal verification.

## Guardrails

- Do not invent evaluation results or ground truth.
- Do not silently change dataset labels to improve scores.
- Do not compare results produced under materially different conditions without explaining the difference.
- Do not treat correlation as proof of causation.
- Do not establish unapproved release thresholds.
- Do not expose sensitive user content in datasets or evaluation reports.

## Expected Output

An evaluation specification, versioned dataset or test cases where applicable, explicit metric definitions, execution results, failure analysis, and any proposed acceptance criteria.

## Completion Checklist

- [ ] Objective and scope are explicit.
- [ ] Dataset references and labels are justified.
- [ ] Metrics have clear definitions.
- [ ] Critical legal failures are visible.
- [ ] Evaluation conditions are recorded.
- [ ] Results and limitations are reported accurately.
