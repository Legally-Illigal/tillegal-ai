"""Create a new annotation-contract draft from T5, preserving all original files."""

import argparse
import hashlib
import json
from pathlib import Path

from ai_core.bm25_retrieval import load_index
from ai_core.evidence_builder import EvidenceBuilder
from ai_core.retrieval_evaluation import EvaluationCorpus, validate_dataset

from src.applications.tillegal.evaluation.annotations import Annotation, Span


def export(dataset_path, index_path, output):
    source_bytes = dataset_path.read_bytes()
    dataset = json.loads(source_bytes)
    corpus = EvaluationCorpus(load_index(index_path))
    builder = EvidenceBuilder(corpus.index)
    validate_dataset(dataset, corpus)
    records = []
    for case in dataset["cases"]:
        spans = []
        for entry in case["evidence"]:
            chunk = corpus.chunks[entry["chunk_id"]]
            version = chunk["document_version_id"]
            # Source-only assembly reuses the pinned builder; no query or ranking is executed.
            evidence = builder._evidence(chunk)
            spans.append(
                Span(
                    evidence_id=evidence["evidence_id"],
                    document_id=chunk["document_id"],
                    document_version_id=version,
                    source_id=evidence["document"]["source_id"],
                    quote_sha256=entry["text_sha256"],
                    article=chunk["article"],
                    clause=chunk["clause"],
                    point=chunk["point"],
                    start=entry["start"],
                    end=entry["end"],
                )
            )
        records.append(
            Annotation(
                question_id=case["question_id"],
                question=case["question"],
                legal_domain="labour",
                query_intent="snapshot_lookup",
                provenance="draft",
                spans=spans,
                temporal_applicability="UNKNOWN",
            ).model_dump()
        )
    if dataset_path.read_bytes() != source_bytes:
        raise ValueError("Source changed during export")
    with output.open("x", encoding="utf8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(
        json.dumps(
            {
                "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
                "draft_records": len(records),
                "approved": 0,
                "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            }
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ("dataset", "index", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    export(args.dataset, args.index, args.output)
