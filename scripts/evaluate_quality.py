"""Score annotations and predictions with validated provenance and reproducible manifest."""

import argparse
import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from src.applications.tillegal.evaluation.annotations import Annotation, Prediction
from src.applications.tillegal.evaluation.quality_metrics import evaluate_case, summarize, wilson


class Experiment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_version: str = Field(min_length=1)
    index_version: str = Field(min_length=1)
    index_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    model: str
    model_revision: str | None
    retrieval_config: dict
    prompt_version: str
    configuration_version: str
    workflow: str
    independent_samples: bool = False
    price_per_million: dict[str, float] | None = None


def run(labels_path, predictions_path, experiment_path, output, k=5):
    if output.exists():
        raise ValueError("New output path required")
    labels_bytes, predictions_bytes = labels_path.read_bytes(), predictions_path.read_bytes()
    labels = [Annotation.model_validate(row) for row in json.loads(labels_bytes)]
    predictions = [Prediction.model_validate(row) for row in json.loads(predictions_bytes)]
    if len({a.question_id for a in labels}) != len(labels) or len({p.question_id for p in predictions}) != len(
        predictions
    ):
        raise ValueError("Duplicate question IDs")
    if {a.question_id for a in labels} != {p.question_id for p in predictions}:
        raise ValueError("All questions require a prediction record, including failures")
    experiment = Experiment.model_validate_json(experiment_path.read_bytes())
    by_id = {p.question_id: p for p in predictions}
    rows = [evaluate_case(a, by_id[a.question_id], k) for a in labels]
    classifications = {}
    for category in sorted({a.provenance for a in labels}):
        subset = [r for r in rows if r["classification"] == category]
        aggregated = {}
        for key in subset[0]["metrics"]:
            values = [r["metrics"][key] for r in subset if r["metrics"][key] is not None]
            aggregated[key] = {"value": sum(values) / len(values) if values else None, "scored_cases": len(values)}
        abstention = [
            r["metrics"]["abstention_accuracy"] for r in subset if r["metrics"]["abstention_accuracy"] is not None
        ]
        classifications[category] = {
            "macro_metrics": aggregated,
            "abstention_accuracy_wilson95": wilson(
                sum(abstention),
                len(abstention),
                independent=experiment.independent_samples and category in {"human_approved", "held_out"},
            ),
            "ci_scope": "Only binomial abstention accuracy; requires >=30 independent reviewed cases",
        }
    result = {
        "manifest": experiment.model_dump(),
        "dataset_sha256": hashlib.sha256(labels_bytes).hexdigest(),
        "predictions_sha256": hashlib.sha256(predictions_bytes).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "classifications": classifications,
        "operational": summarize(predictions, experiment.price_per_million),
        "cases": rows,
        "failure_taxonomy": {
            "failed_requests": sum(p.failed for p in predictions),
            "missing_quality_labels": sum(a.provenance in {"draft", "exploratory"} for a in labels),
        },
    }
    with output.open("x", encoding="utf8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("labels", "predictions", "experiment", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    run(args.labels, args.predictions, args.experiment, args.output, args.k)
