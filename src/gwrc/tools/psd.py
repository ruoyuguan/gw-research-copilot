"""Validation of real one-dimensional auto power spectral densities."""

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Literal

import numpy as np

from gwrc.core.numeric import as_numeric_array
from gwrc.core.results import ValidationMessage, messages_to_dict

FrequencyOrder = Literal["increasing", "decreasing", "unordered"]


@dataclass(frozen=True)
class PSDTolerances:
    """Allowed negative auto-spectrum values, in PSD units."""

    atol: float = 0.0
    rtol: float = 0.0

    def __post_init__(self) -> None:
        """Require finite, non-negative numerical tolerances."""
        for name, value in vars(self).items():
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")

    def to_dict(self) -> dict[str, float]:
        """Return the tolerance policy used by the checker."""
        return dict(vars(self))


@dataclass(frozen=True)
class PSDReport:
    """Diagnostics for array properties and user-supplied PSD declarations."""

    frequency_shape: tuple[int, ...]
    psd_shape: tuple[int, ...]
    is_real_valued: bool
    shape_matches: bool
    is_finite: bool
    metadata_complete: bool
    frequency_unique: bool | None = None
    frequency_order_matches: bool | None = None
    frequency_convention_consistent: bool = False
    nonnegative: bool = False
    minimum_frequency: float | None = None
    maximum_frequency: float | None = None
    minimum_psd: float | None = None
    negative_psd_tolerance: float | None = None
    expected_order: FrequencyOrder = "increasing"
    declarations: dict[str, str | None] = field(default_factory=dict)
    tolerances: PSDTolerances = field(default_factory=PSDTolerances)
    errors: tuple[ValidationMessage, ...] = ()
    warnings: tuple[ValidationMessage, ...] = ()

    @property
    def valid(self) -> bool:
        """Whether the requested checks pass under the explicit conventions."""
        return (
            self.is_real_valued
            and self.shape_matches
            and self.is_finite
            and self.metadata_complete
            and self.frequency_unique is True
            and self.frequency_order_matches is not False
            and self.frequency_convention_consistent
            and self.nonnegative
        )

    def to_dict(self) -> dict[str, Any]:
        """Return strict JSON-compatible PSD diagnostics."""
        return {
            "valid": self.valid,
            "spectrum_kind": "auto",
            "frequency_shape": list(self.frequency_shape),
            "psd_shape": list(self.psd_shape),
            "is_real_valued": self.is_real_valued,
            "shape_matches": self.shape_matches,
            "is_finite": self.is_finite,
            "metadata_complete": self.metadata_complete,
            "frequency_unique": self.frequency_unique,
            "expected_frequency_order": self.expected_order,
            "frequency_order_matches": self.frequency_order_matches,
            "frequency_convention_consistent": self.frequency_convention_consistent,
            "nonnegative": self.nonnegative,
            "minimum_frequency": self.minimum_frequency,
            "maximum_frequency": self.maximum_frequency,
            "minimum_psd": self.minimum_psd,
            "negative_psd_tolerance": self.negative_psd_tolerance,
            "declarations": self.declarations,
            "tolerances": self.tolerances.to_dict(),
            "errors": messages_to_dict(self.errors),
            "warnings": messages_to_dict(self.warnings),
            "scope": (
                "Array and declaration checks only; physical units, Fourier "
                "normalization, and detector response are not independently verified."
            ),
        }


def check_psd(
    frequency: Any,
    psd: Any,
    *,
    frequency_unit: str | None,
    psd_unit: str | None,
    psd_definition: str | None,
    spectral_convention: str | None,
    fourier_convention: str | None = None,
    expected_order: FrequencyOrder = "increasing",
    tolerances: PSDTolerances | None = None,
) -> PSDReport:
    """Check a real auto-spectrum without changing its spectral convention.

    Required declarations are checked for presence, not scientifically proven.
    ``unordered`` disables only the monotonicity requirement; finite, unique
    frequencies remain mandatory.
    """
    if expected_order not in ("increasing", "decreasing", "unordered"):
        raise ValueError(f"unsupported frequency order: {expected_order!r}")
    tolerances = tolerances or PSDTolerances()
    errors: list[ValidationMessage] = []
    warnings: list[ValidationMessage] = []
    arrays: dict[str, np.ndarray | None] = {}
    shapes: dict[str, tuple[int, ...]] = {}
    for name, values in (("frequency", frequency), ("psd", psd)):
        try:
            array = as_numeric_array(values, name=name)
            arrays[name] = array
            shapes[name] = tuple(array.shape)
        except ValueError as exc:
            arrays[name] = None
            shapes[name] = ()
            errors.append(ValidationMessage(f"invalid_{name}", str(exc)))

    frequency_array = arrays["frequency"]
    psd_array = arrays["psd"]
    arrays_present = frequency_array is not None and psd_array is not None
    real_valued = arrays_present and not (
        np.iscomplexobj(frequency_array) or np.iscomplexobj(psd_array)
    )
    if arrays_present and not real_valued:
        errors.append(
            ValidationMessage(
                "complex_auto_spectrum",
                "frequency and auto-spectrum inputs must be explicitly real-valued",
            )
        )

    shape_matches = bool(
        arrays_present
        and frequency_array.ndim == 1
        and psd_array.ndim == 1
        and frequency_array.size > 0
        and frequency_array.shape == psd_array.shape
    )
    if not shape_matches:
        errors.append(
            ValidationMessage(
                "shape_mismatch",
                "frequency and PSD must be non-empty one-dimensional arrays "
                "of equal length",
            )
        )

    finite = bool(
        arrays_present
        and np.all(np.isfinite(frequency_array))
        and np.all(np.isfinite(psd_array))
    )
    if arrays_present and not finite:
        errors.append(
            ValidationMessage(
                "non_finite", "frequency and PSD values must all be finite"
            )
        )

    raw_declarations = {
        "frequency_unit": frequency_unit,
        "psd_unit": psd_unit,
        "psd_definition": psd_definition,
        "spectral_convention": spectral_convention,
        "fourier_convention": fourier_convention,
    }
    declarations = {
        key: value.strip() if isinstance(value, str) else None
        for key, value in raw_declarations.items()
    }
    required = (
        "frequency_unit",
        "psd_unit",
        "psd_definition",
        "spectral_convention",
    )
    missing = [key for key in required if not declarations[key]]
    if missing:
        errors.append(
            ValidationMessage(
                "missing_declarations",
                "missing or empty declarations: " + ", ".join(missing),
            )
        )
    convention = declarations["spectral_convention"]
    if convention is not None:
        convention = convention.lower()
        declarations["spectral_convention"] = convention
    if convention is not None and convention not in ("one-sided", "two-sided"):
        errors.append(
            ValidationMessage(
                "invalid_spectral_convention",
                "spectral_convention must be 'one-sided' or 'two-sided'",
            )
        )
    if fourier_convention is not None and not declarations["fourier_convention"]:
        errors.append(
            ValidationMessage(
                "invalid_fourier_convention",
                "fourier_convention must be a non-empty string when supplied",
            )
        )
    metadata_complete = not any(
        message.code
        in {
            "missing_declarations",
            "invalid_spectral_convention",
            "invalid_fourier_convention",
        }
        for message in errors
    )

    unique: bool | None = None
    order_matches: bool | None = None
    convention_consistent = False
    minimum_frequency: float | None = None
    maximum_frequency: float | None = None
    if (
        frequency_array is not None
        and not np.iscomplexobj(frequency_array)
        and frequency_array.ndim == 1
        and frequency_array.size > 0
        and np.all(np.isfinite(frequency_array))
    ):
        minimum_frequency = float(np.min(frequency_array))
        maximum_frequency = float(np.max(frequency_array))
        unique = bool(np.unique(frequency_array).size == frequency_array.size)
        if not unique:
            errors.append(
                ValidationMessage(
                    "duplicate_frequency", "frequency values must be unique"
                )
            )
        differences = np.diff(frequency_array)
        if expected_order == "increasing":
            order_matches = bool(np.all(differences > 0))
        elif expected_order == "decreasing":
            order_matches = bool(np.all(differences < 0))
        if order_matches is False:
            errors.append(
                ValidationMessage(
                    "frequency_order",
                    f"frequency is not strictly {expected_order}",
                )
            )
        if convention == "one-sided":
            convention_consistent = minimum_frequency >= 0
            if not convention_consistent:
                errors.append(
                    ValidationMessage(
                        "negative_one_sided_frequency",
                        "a one-sided auto-spectrum cannot use negative frequencies",
                    )
                )
        elif convention == "two-sided":
            convention_consistent = True

    minimum_psd: float | None = None
    negative_tolerance: float | None = None
    nonnegative = False
    if (
        psd_array is not None
        and not np.iscomplexobj(psd_array)
        and psd_array.size > 0
        and np.all(np.isfinite(psd_array))
    ):
        minimum_psd = float(np.min(psd_array))
        psd_scale = float(np.max(np.abs(psd_array)))
        negative_tolerance = max(
            tolerances.atol, tolerances.rtol * psd_scale
        )
        nonnegative = minimum_psd >= -negative_tolerance
        if minimum_psd < 0 and nonnegative:
            warnings.append(
                ValidationMessage(
                    "negative_psd_tolerated",
                    "a small negative auto-spectrum value was accepted by tolerance",
                )
            )
        elif not nonnegative:
            errors.append(
                ValidationMessage(
                    "negative_psd",
                    f"minimum auto-spectrum value {minimum_psd:.6g} is below "
                    f"-{negative_tolerance:.6g}",
                )
            )

    return PSDReport(
        frequency_shape=shapes["frequency"],
        psd_shape=shapes["psd"],
        is_real_valued=real_valued,
        shape_matches=shape_matches,
        is_finite=finite,
        metadata_complete=metadata_complete,
        frequency_unique=unique,
        frequency_order_matches=order_matches,
        frequency_convention_consistent=convention_consistent,
        nonnegative=nonnegative,
        minimum_frequency=minimum_frequency,
        maximum_frequency=maximum_frequency,
        minimum_psd=minimum_psd,
        negative_psd_tolerance=negative_tolerance,
        expected_order=expected_order,
        declarations=declarations,
        tolerances=tolerances,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
