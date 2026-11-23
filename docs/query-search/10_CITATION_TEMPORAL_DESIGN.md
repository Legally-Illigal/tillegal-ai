# Citation identity and temporal roles

## Decision and alternatives

Rule-only date extraction cannot assign every legal role. Model-only extraction demonstrated Q025's document-number-as-time error. A full legal ontology/source resolver would exceed the evidence and scope. Selected solution: **literal deterministic spans plus bounded semantic planning and strict validation**. The model receives grounded reference/temporal candidates but does not create trusted source metadata.

`query/context.py::parse_context` reads the NFC/trimmed analysis text without removing substrings. `original` retains the exact caller string. start/end are offsets into this documented analysis text, not arbitrary offsets into NFD/original whitespace. QueryPlan.context_and_links rechecks each span against that text.

## Types

- LegalReference: kind=document/article/clause/point/statute_reference, text, start, end, source=user_supplied_unverified. Document numbers such as45/2019/QH14 are not dates. Article/clause/point identifiers are kept separately. A named statute plus year is a reference hint; it is not resolved to an invented document number or enactment date.
- TemporalContext: text/start/end, role, iso_date when an explicit full valid calendar date exists, and negated. ISO strings remain JSON-serializable for old CLI/evaluator callers.
- Roles distinguish event_date, applicability_date, publication_date (including explicit enactment cues), effective_date, historical_reference, relative_reference, duration, current_reference and unspecified. Nearest explicit lexical cues are used; uncertain dates remain unspecified. Cues are not an expert legal interpretation.
- Publication/effective dates are user-supplied statements, not externally confirmed statutory metadata. A year alone never creates a calendar day/as_of_date.

## Model boundary

`classify_model_time` classifies actual occurrences rather than deleting a document number from the question. Reference-only spans are moved out of the legacy temporal list with MODEL_REFERENCE_RECLASSIFIED; unsupported dates remain errors. If the same year occurs in a reference and a real event, the event occurrence remains temporal. A negated current-time reference stays visible in typed context but is not an active temporal request.

The narrowed provider intent enum is retained: exact lookups exit before semantic invocation, so model requests accept legal_question only. Runtime checks remain in place. Punctuation/paraphrase errors in facts are still rejected rather than normalized into plausible facts.

Actual offline parser output, generated from code:

```json
{
  "original": "Tôi ký hợp đồng lao động ngày 15/03/2024 theo Điều 35 Bộ luật Lao động 45/2019/QH14.",
  "citations": [
    {
      "kind": "article",
      "text": "Điều 35",
      "start": 46,
      "end": 53,
      "source": "user_supplied_unverified"
    },
    {
      "kind": "document",
      "text": "45/2019/QH14",
      "start": 71,
      "end": 83,
      "source": "user_supplied_unverified"
    }
  ],
  "temporal_context": [
    {
      "text": "15/03/2024",
      "start": 30,
      "end": 40,
      "role": "event_date",
      "iso_date": "2024-03-15",
      "negated": false
    }
  ],
  "temporal_scope": [
    "15/03/2024"
  ]
}
```

## Compatibility and regression coverage

Original QueryPlan fields remain. Four additive metadata fields have defaults: citations, temporal_context, search_objectives, planning_warnings. Old plans without them still load. Existing exact-key tests were deliberately extended; external callers that forbid additional JSON keys may need to accept these documented additions. Native Retrieval contracts are unchanged.

Tests cover45/2019/QH14; Điều35 Bộ luật Lao động2019; Khoản2 Điều10; multiple citations; event dates next to citations; a statute year without an applicability date; historical context; same year in a statute/event; publication/effectivity/applicability cues; negation; Unicode/source offsets; novel dates/sources rejected. Live Q025 passed; unrelated event dates were preserved. No legal identity/existence/effectiveness is asserted from the text alone.

Limitations: title/year recognition and nearest-cue role assignment are narrow heuristics. Ambiguous references are not automatically bound to documents across clauses. Relative dates are not converted into days. SearchOptions still require the caller to supply an explicit trusted date.
