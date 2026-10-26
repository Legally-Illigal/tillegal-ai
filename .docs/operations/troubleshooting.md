# Troubleshooting

## 1. General Procedure

1. Identify the affected environment, release, workflow version, time window, and request/run ID.
2. Check service health and readiness.
3. Inspect structured logs and workflow events.
4. Determine whether the issue originates in application logic, configuration, retrieval, a model provider, or an external dependency.
5. Preserve relevant evidence while redacting secrets and sensitive content.
6. Apply the smallest safe mitigation and verify recovery.
7. Record the cause, or the remaining investigation steps, for follow-up.

Avoid unbounded retries. Follow the configured timeout, retry, fallback, and budget policies.

## 2. Common Symptoms

| Symptom | Investigation | Safe response |
|---|---|---|
| Service fails to start | Missing configuration, dependency errors, invalid settings | Correct the reported configuration or dependency issue |
| Readiness check fails | Required dependency health and connection settings | Identify the failing dependency before restarting repeatedly |
| Model call times out | Provider status, network, prompt size, concurrency, timeout settings | Apply bounded retry/fallback policy |
| Provider rate limit | Provider error, quota, request burst, concurrency | Back off within policy or use an approved fallback |
| Invalid model output | Schema validation, model profile, prompt version, parsing errors | Reject invalid output or use a bounded repair attempt |
| Retrieval returns no useful evidence | Query parsing, filters, index freshness, retrieval configuration | Inspect evidence IDs and retrieval evaluation results |
| Citation cannot be verified | Source availability, citation extraction, legal document/version metadata | Preserve an unverified state; do not claim verification succeeded |
| Workflow runs too long | Node transitions, repeated search/judge decisions, execution budget | Stop at the configured limit and record the stop reason |
| Token usage or cost rises unexpectedly | Model routing, prompt size, retry frequency, traffic | Contain the source and review telemetry before changing configuration |
| Legal-answer quality regresses | Model, prompt, workflow, retrieval, evidence, and verification versions | Run the regression suite and consider rollback |

## 3. Evidence Checklist

Capture applicable information:

- request ID and workflow run ID;
- timestamp and environment;
- release commit and workflow version;
- prompt/model profile versions;
- node transition sequence and stop reason;
- safe error category and stack trace;
- provider request ID, where safe to retain;
- evidence identifiers and verification result;
- relevant evaluation run and case IDs.

Never attach credentials, raw authorization headers, or unrestricted legal/user documents to an issue.

## 4. Escalation

Treat an issue as a potential incident if it:

- affects multiple users or causes sustained unavailability;
- exposes secrets or sensitive information;
- causes uncontrolled provider spend;
- may have returned materially incorrect legal bases or citations;
- indicates that required verification can be bypassed.

Follow `incident-response.md` when escalation is warranted.

## 5. Related Documents

- `../development/debugging.md`
- `monitoring.md`
- `incident-response.md`
- `deployment.md`
