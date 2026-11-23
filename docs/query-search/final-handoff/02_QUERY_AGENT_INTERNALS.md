# Query Agent internals

## Deterministic path: agent.py:understand

Input is a string1–10000 chars; invalid type, empty/blank/control-surrogate text raises QueryInputError with a safe code. Analyze NFC/trimmed text but preserve caller argument byte-for-character in original (Python string, not raw encoded bytes). Splitting uses bounded question punctuation and selected conjunctions. Over4 parts or unclear/invalid-date input produces clarification rather than executing arbitrary search.

Exact citation/quote lookup preserves requested content and skips semantic provider. Ordinary questions use deterministic subqueries; selected labour topic expansions and a deliberately narrow employee-exit pattern can generate two issues/facts/missing questions. This is not a general legal ontology; domain only labour/unknown. Original is preserved even where facts extraction is sparse.

## Typed reference/time parsing: context.py

parse_context recognizes document numbers, article/clause/point and limited statute-name/year forms; outputs user_supplied_unverified references. Calendar dates/years/durations/relative phrases are separate temporal spans. Nearest lexical cue selects event/applicability/publication/effective/history roles. Invalid calendar candidates are not converted into dates. It never infers effective dates from document years. Offsets refer to NFC/trimmed analysis text.

classify_model_time checks literal grounding, distinguishes actual time from reference-only mentions and negated time. Reclassified document-as-time produces MODEL_REFERENCE_RECLASSIFIED; negated temporal mention produces NEGATED_TEMPORAL_REFERENCE_IGNORED. Role extraction and negation remain heuristic, not full linguistic/legal interpretation.

## Gemini activation and protocol

create_query_search(...semantic_mode="gemini") calls query/gemini.py:create_gemini_query_agent. Config profile query_semantic uses provider gemini, api_key_env GOOGLE_API_KEY, current configured model gemini-3.5-flash-lite, max_output_tokens4096. GEMINI_MODEL and QUERY_LLM_TIMEOUT_SECONDS override model/deadline; settings validate them. Max timeout120 seconds, token range128–8192. Existing provider timeout30 seconds; manually constructed SemanticQueryAgent defaults15 seconds. This audit does not assert current remote model availability: prior real calls succeeded; no new provider call was needed.

Factory reads process env by default and does not load/rewrite.env itself; caller can explicitly load dotenv without override or pass environ to create_gemini_query_agent. Only Query profile is consumed. configs/models.yaml still has OpenAI defaults/profiles for other modules, which do not change this Query Gemini path.

StructuredCompletion is an injectable async callable returning JSON text. GeminiStructuredCompletion delegates to LiteLLM acompletion(model="gemini/"+model, messages, response_format with response_schema), no retry/cache, no-log. Finish reason must be stop, content bounded32000 chars and JSON object. Provider exceptions are safe machine codes; SemanticQueryAgent wraps generic provider failure as QUERY_ANALYSIS_PROVIDER_ERROR, timeout as QUERY_ANALYSIS_TIMEOUT. Adapter HTTP code may exist internally but is not promised on QueryAnalysisError. Cancellation propagates. No silent deterministic fallback.

## Semantic validation order

1. Run deterministic understand first; clarification and exact lookup short circuit.
2. Pass normalized question plus literal reference/time/slot hints; constrain model intent to legal_question.
3. Bound completion with asyncio timeout.
4. SemanticAnalysis.model_validate_json rejects extra fields; StatedFact requires text==source_quote.
5. Each source_quote must occur literally in normalized question.
6. Classify temporal mentions, reject unsupported time/citation/numeric additions in generated issue/query/missing/clarification text.
7. Deduplicate query strings, build query_index→issue_indices; append selected exact shared context under a bounded fact budget.
8. reconcile_missing removes selected redundant slot questions/adds narrow employee-exit followups; not domain-complete.
9. Preserve omitted user citation spans for a single objective; do not blanket-copy all citations into unrelated multiple queries.
10. Construct QueryPlan; validate supplied span slice/mapping invariants, return dict.

Gemini generates SemanticAnalysis facts/issues/query/missing/temporal mentions/clarification. Citation/time typed spans are deterministic; objective links and warnings are postprocessing. Schema/grounding checks are guards, not proof of comprehensive issues or legally correct wording. “Trái pháp luật” in a search topic is not a conclusion that the user acted unlawfully.

## Public schema trust limitation

QueryPlan uses ordinary BaseModel defaults, not extra=forbid or globally strict coercion. Semantic payload models and SearchOptions are stricter. Direct QueryPlan.model_validate on an externally crafted object does not rerun planner fact grounding. A controlled probe confirms a citation end offset beyond text length can pass when Python slicing still matches the suffix; parser-produced spans are correct. This is a nonblocking boundary limitation of manual plan ingestion, not changed in this acceptance scope. Prefer planner output; do not treat externally supplied plans as inherently trusted because schema parsing succeeded. Details in contract_probes.json and07.

## Historical semantic result limits

Q025 correctly retains45/2019/QH14 without invented temporal applicability. Q019 negated current time is preserved as negated context. Q007 primary raw response remains rejected due to grounding/punctuation mismatch; variability output is separate. Earlier missing-info proxy regressed8/12→7/12. No new prompt/quality optimization and no claim Gemini universally outperforms deterministic.
