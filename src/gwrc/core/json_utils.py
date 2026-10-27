"""Strict JSON conversion that never emits NaN or infinity."""

import json
import math
from typing import Any


def to_builtin(value: Any) -> Any:
    """Convert NumPy values and containers to strict JSON-compatible values."""
    value_module = type(value).__module__
    if value_module == "numpy" or value_module.startswith("numpy."):
        import numpy as np

        if isinstance(value, np.generic):
            return to_builtin(value.item())
        if isinstance(value, np.ndarray):
            return to_builtin(value.tolist())
    if isinstance(value, complex):
        raise TypeError("Complex values require an explicit real/imaginary schema")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Non-finite floats are not valid JSON results")
        return value
    if isinstance(value, dict):
        return {str(key): to_builtin(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_builtin(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"Unsupported JSON value type: {type(value).__name__}")


def json_text(value: Any) -> str:
    """Render deterministic, human-readable, standards-compliant JSON."""
    return json.dumps(
        to_builtin(value), ensure_ascii=False, indent=2, allow_nan=False
    ) + "\n"
