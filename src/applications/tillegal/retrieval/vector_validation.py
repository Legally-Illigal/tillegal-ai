"""Numeric contract shared by query encoders and their application caller."""

import math

from src.applications.tillegal.retrieval.document_models import EMBEDDING_DIMENSION


def validate_query_vector(values: tuple[float, ...]) -> tuple[float, ...]:
    """Reject malformed encoder output; never silently normalize or truncate it."""
    if len(values) != EMBEDDING_DIMENSION:
        raise ValueError("Query embedding must have 384 dimensions")
    if any(
        isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) for value in values
    ):
        raise ValueError("Query embedding must contain finite numbers")
    vector = tuple(float(value) for value in values)
    norm = math.sqrt(sum(value * value for value in vector))
    if not math.isfinite(norm) or abs(norm - 1) > 1e-4:
        raise ValueError("Query embedding must be L2 normalized")
    return vector
