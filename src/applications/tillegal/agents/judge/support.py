"""Minimal local JSON/provider primitives selected from the legacy Judge dependencies."""

import json
from copy import deepcopy


class ContractError(ValueError):
    pass


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


class GenerationError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class GenerationText(str):
    """Backward-compatible string with request-local provider telemetry."""

    def __new__(cls, text, metadata):
        value = super().__new__(cls, text)
        value.metadata = deepcopy(metadata)
        return value


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def constant(_):
        raise ValueError("non-finite JSON constant")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
