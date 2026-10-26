# Dependency Rules

> Rules for maintaining a small, testable Python AI Service with a reusable framework layer.

## 1. Dependency direction

Use this conceptual direction:

```text
API / entry points
      ↓
Tillegal application workflows and use cases
      ↓
Reusable framework abstractions
      ↓
Integration adapters (LLM provider, retrieval store, telemetry, persistence)
```

The exact package layout may evolve, but dependency direction must remain explicit. Adapter implementations can implement framework/application-facing interfaces; high-level workflow code should not depend on a concrete provider SDK or database client.

## 2. Rules

1. **Framework must not import Tillegal domain logic.** Generic workflow, model gateway, prompt utilities, telemetry and evaluation interfaces must remain reusable.
2. **Tillegal modules may use framework abstractions.** Legal-specific policies, schemas, prompts, agents and evaluators belong in the application layer.
3. **Provider SDKs stay behind adapters.** Application nodes call the shared LLM gateway rather than importing a provider SDK directly.
4. **External-service details stay at boundaries.** Normalize provider-specific errors, usage fields and response shapes before exposing them to workflow code.
5. **Contracts are code-validated.** Validate incoming requests, graph state transitions and LLM structured outputs. Prompts alone are not a contract.
6. **Orchestrator owns control state.** Agents may propose queries or outcomes, but may not directly increase search/retry budgets or change termination state arbitrarily.
7. **Evidence identity is immutable.** Do not rewrite source evidence or reuse IDs to make an unverified citation appear verified.
8. **Untrusted content is data.** Retrieved web/legal text must not override system policies, tool permissions, workflow goals or budgets.
9. **Secrets never enter prompts or ordinary logs.** Use environment/secret configuration and redact credentials, access tokens and API keys.
10. **No unbounded loops or retries.** Every retry, search round, repair pass and model call must be bounded by policy.
11. **Fallback does not bypass verification.** Outputs from a fallback model must pass the same schema and verification gates.
12. **No silent success on partial failure.** Keep per-claim/per-citation errors and `stop_reason` visible in structured results.
13. **No hidden coupling through globals.** Pass request context, dependencies and configuration explicitly; avoid mutable global model clients/state.
14. **Test boundaries with fakes.** Unit tests should not require live LLM API keys or real provider calls.
15. **Avoid premature distributed architecture.** Do not introduce queues, multiple deployable services, or mandatory infrastructure without a documented need.

## 3. Allowed and disallowed examples

| Situation | Preferred | Avoid |
|---|---|---|
| Agent needs a model | `LLMGateway.generate(...)` / typed gateway interface | Importing a provider SDK inside the Agent |
| Agent needs legal data | Retrieval port/interface | Embedding database connection logic inside prompt/node code |
| Need usage/cost | Normalized usage/telemetry record | Parsing provider response independently in every Agent |
| Need another search round | Return a proposal/status to Orchestrator | Agent mutating global counters or launching an unbounded loop |
| Model returns malformed JSON | Validate, handle typed failure, optionally bounded repair | Passing malformed content to the next node |
| Source does not support a claim | Mark unsupported/uncertain and route to repair or limitation | Editing the citation text to make it appear supported |
| Test graph | Inject fake gateway/retriever | Requiring network/API access for every test |

## 4. Handling unresolved design choices

Do not infer an accepted decision from a technology being mentioned as an option. Record durable implementation choices in ADRs, and keep integrations behind small interfaces when practical.

The accepted implementation uses LangGraph for workflow orchestration and LiteLLM behind the shared model gateway. Supabase Postgres with pgvector is the selected RAG vector store; access it through an adapter.

## 5. Change discipline

Before changing a dependency boundary:
1. Identify which reusable or domain-specific responsibility changes.
2. Check affected interfaces and tests.
3. Update the relevant architecture summary/ADR if the change is durable.
4. Report unresolved contradictions between project documentation, code, and configuration rather than silently changing approved decisions.
