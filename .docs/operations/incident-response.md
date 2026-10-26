# Incident Response

## 1. Purpose

Provide a consistent process for responding to incidents affecting availability, security/privacy, operational cost, or legal-answer reliability.

Use the team's approved severity definitions and communication channels where they exist. This document does not assume a particular on-call structure or service-level objective.

## 2. Incident Categories

- **Availability:** service outage, repeated crashes, dependency outage.
- **Reliability:** repeated timeouts, malformed output, workflow failure, runaway retries.
- **Legal quality:** materially incorrect legal basis, misleading citation, verification bypass, severe evaluation regression.
- **Security/privacy:** exposed credentials, unauthorized access, sensitive content disclosed or logged improperly.
- **Cost/capacity:** unexpected provider spending, quota exhaustion, concurrency overload.

## 3. Response Stages

### 3.1 Detect and Acknowledge

- Record the first known occurrence and detection source.
- Identify the environment, release, and affected functionality.
- Create an incident record with a unique incident ID.
- Assign an incident lead when an appropriate team member is available.

### 3.2 Triage and Contain

- Estimate scope, duration, severity, and potential user impact.
- Stop a risky rollout or reduce traffic when necessary.
- Disable a faulty model profile or workflow path only through a controlled change.
- Revoke and rotate credentials if they may have been exposed.
- For legal-quality incidents, preserve request IDs, evidence IDs, workflow versions, and verification results.
- Restrict access to sensitive incident evidence.

### 3.3 Recover

- Roll back to a known-good artifact/configuration or apply a reviewed mitigation.
- Verify service health and run smoke tests.
- For legal-quality incidents, run relevant regression cases and confirm that required verification remains enforced.
- Do not declare full recovery until the applicable checks pass.

### 3.4 Communicate

Communicate known facts, current impact, mitigation, and the next update time through the agreed team channel.

Clearly distinguish confirmed facts from hypotheses. Do not speculate about impact or cause.

### 3.5 Close and Learn

Record the timeline, impact, cause or leading hypothesis, recovery steps, and follow-up actions. Assign owners and track actions to completion.

## 4. Severity Guidance

Use the team's approved incident severity policy. If none exists, assess severity proportionally based on:

- number of affected users and duration;
- data sensitivity and possible exposure;
- potential harm from incorrect legal bases or citations;
- financial impact or uncontrolled provider spend;
- availability of a safe workaround.

Potential credential exposure, sensitive-data disclosure, or a systemic path that bypasses legal verification requires prompt escalation even if the service remains available.

## 5. Post-Incident Actions

- Add a regression test for the failure mode.
- Add or tune alerts where they provide actionable signals.
- Update deployment and troubleshooting instructions.
- Review access controls, retention, and redaction if data exposure was involved.
- Update relevant ADRs if the architectural decision changes.
- Track corrective actions to completion and verify their effectiveness.

## 6. Incident Record Template

- Incident ID:
- Start/end time:
- Category/severity:
- Affected environment and release:
- Impact:
- Detection source:
- Timeline:
- Containment and recovery:
- Root cause or current hypothesis:
- Evidence and evaluation results:
- Follow-up actions and owners:

## 7. Related Documents

- `deployment.md`
- `monitoring.md`
- `troubleshooting.md`
