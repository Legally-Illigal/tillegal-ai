"""Metric primitives with explicit missing-label behavior."""

import math

from src.applications.tillegal.evaluation.annotations import Annotation, Prediction


def percentile(values, p):
    if not values:
        return None
    if not 0 < p <= 1 or any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("finite nonnegative observations and percentile in (0,1] required")
    return sorted(values)[math.ceil(len(values) * p) - 1]


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def retrieval(ranked, relevant, k):
    if k < 1 or len(set(ranked)) != len(ranked):
        raise ValueError("positive k and unique ranked units required")
    if relevant is None:
        return dict(recall=None, precision=None, mrr=None, ndcg=None)
    gold = set(relevant)
    hits = [i for i, u in enumerate(ranked[:k], 1) if u in gold]
    dcg = sum(1 / math.log2(i + 1) for i in hits)
    ideal = sum(1 / math.log2(i + 1) for i in range(1, min(k, len(gold)) + 1))
    return {
        "recall": ratio(len(hits), len(gold)),
        "precision": len(hits) / k,
        "mrr": 1 / hits[0] if hits else 0.0,
        "ndcg": ratio(dcg, ideal),
    }


def span_covered(target, context):
    matches = sorted(
        (s.start, s.end)
        for s in context
        if all(
            getattr(s, k) == getattr(target, k)
            for k in ("evidence_id", "document_id", "document_version_id", "source_id", "quote_sha256")
        )
    )
    cursor = target.start
    for start, end in matches:
        if start > cursor:
            break
        if end > cursor:
            cursor = end
        if cursor >= target.end:
            return True
    return False


def span_recall(targets, context, role=None):
    if targets is None:
        return None
    targets = [s for s in targets if role is None or s.role == role]
    return ratio(sum(span_covered(s, context) for s in targets), len(targets))


def evaluate_case(annotation: Annotation, prediction: Prediction, k=5):
    if annotation.question_id != prediction.question_id:
        raise ValueError("question identity mismatch")
    reviewed = annotation.provenance in {"human_approved", "held_out", "synthetic"}
    metrics = retrieval(prediction.ranked_units, annotation.relevant_units if reviewed else None, k)
    metrics.update(
        context_coverage=None,
        condition_recall=None,
        exception_recall=None,
        claim_support_accuracy=None,
        citation_correctness=None,
        abstention_accuracy=None,
    )
    denominators = {}
    if reviewed:
        metrics.update(
            context_coverage=span_recall(annotation.spans, prediction.context),
            condition_recall=span_recall(annotation.spans, prediction.context, "condition"),
            exception_recall=span_recall(annotation.spans, prediction.context, "exception"),
        )
        labels = {c.claim_id: c for c in annotation.claims or [] if c.verdict != "NOT_EVALUATED"}
        by_id = {c.claim_id: c for c in prediction.claims}
        correct = sum(key in by_id and by_id[key].verdict == label.verdict for key, label in labels.items())
        metrics["claim_support_accuracy"] = ratio(correct, len(labels))
        supported = [c for c in labels.values() if c.verdict == "SUPPORTED"]
        correct_citations = sum(
            c.claim_id in by_id and set(by_id[c.claim_id].evidence_ids) == set(c.evidence_ids) and bool(c.evidence_ids)
            for c in supported
        )
        metrics["citation_correctness"] = ratio(correct_citations, len(supported))
        denominators.update(
            claim_labels=len(labels),
            citation_labels=len(supported),
            unlabelled_predictions=len(set(by_id) - set(labels)),
        )
        if annotation.expected_abstention is not None and prediction.abstained is not None:
            metrics["abstention_accuracy"] = float(annotation.expected_abstention == prediction.abstained)
    return {
        "question_id": annotation.question_id,
        "classification": annotation.provenance,
        "metrics": metrics,
        "denominators": denominators,
        "predicted_verdict_counts": {
            label: sum(c.verdict == label for c in prediction.claims)
            for label in ("SUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE", "NOT_EVALUATED")
        },
    }


def summarize(predictions, price_per_million=None):
    observations = [p.latency_ms for p in predictions]
    tokens = {
        key: sum(getattr(p, key) for p in predictions)
        if predictions and all(getattr(p, key) is not None for p in predictions)
        else None
        for key in ("prompt_tokens", "completion_tokens")
    }
    cost = None
    if price_per_million is not None and all(v is not None for v in tokens.values()):
        if set(price_per_million) != set(tokens) or any(
            not math.isfinite(v) or v < 0 for v in price_per_million.values()
        ):
            raise ValueError("explicit finite nonnegative price required for both token types")
        cost = sum(tokens[k] * price_per_million[k] / 1_000_000 for k in tokens)
    decisions = [p.abstained for p in predictions if p.abstained is not None]
    return {
        "sample_count": len(predictions),
        "failures": sum(p.failed for p in predictions),
        "latency_p50_ms": percentile(observations, 0.5),
        "latency_p95_ms": percentile(observations, 0.95),
        "abstention_coverage": ratio(len(decisions), len(predictions)),
        "abstention_rate": ratio(sum(decisions), len(decisions)),
        "tokens": tokens,
        "estimated_cost": cost,
        "cost_currency": "USD" if cost is not None else None,
    }


def wilson(successes, total, independent=False):
    if not 0 <= successes <= total:
        raise ValueError("invalid binomial counts")
    if not independent or total < 30:
        return None
    z = 1.959963984540054
    p = successes / total
    center = (p + z * z / (2 * total)) / (1 + z * z / total)
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return [center - radius, center + radius]
