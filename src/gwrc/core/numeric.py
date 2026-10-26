"""Explicit double-precision array conversion."""

from typing import Any

import numpy as np
from numpy.typing import NDArray


def as_numeric_array(values: Any, *, name: str) -> NDArray[np.complex128 | np.float64]:
    """Convert a real/complex numeric array, rejecting text and object arrays."""
    try:
        array = np.asarray(values)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a regular numeric array") from exc
    if array.dtype.kind not in "iufc":
        raise ValueError(f"{name} must contain real or complex numbers")
    dtype = np.complex128 if array.dtype.kind == "c" else np.float64
    return np.asarray(array, dtype=dtype)
