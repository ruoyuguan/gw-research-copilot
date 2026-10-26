"""Covariance validation for real and complex double-precision matrices."""

from dataclasses import dataclass, field
from math import isfinite
from typing import Any

import numpy as np

from gwrc.core.numeric import as_numeric_array
from gwrc.core.results import ValidationMessage, messages_to_dict


@dataclass(frozen=True)
class CovarianceTolerances:
    """Numerical thresholds; absolute tolerances have covariance-entry units."""

    symmetry_rtol: float = 1e-10
    symmetry_atol: float = 0.0
    eigenvalue_rtol: float = 1e-10
    eigenvalue_atol: float = 0.0
    rank_rtol: float = 1e-12
    rank_atol: float = 0.0
    condition_warning: float = 1e12

    def __post_init__(self) -> None:
        """Reject thresholds that could hide invalid numerical input."""
        for name, value in vars(self).items():
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if self.condition_warning == 0:
            raise ValueError("condition_warning must be positive")

    def to_dict(self) -> dict[str, float]:
        """Return the complete numerical policy used by a check."""
        return dict(vars(self))


@dataclass(frozen=True)
class CovarianceReport:
    """Separate covariance validity from invertibility and conditioning."""

    shape: tuple[int, ...]
    data_kind: str
    is_numeric: bool
    is_square: bool
    is_finite: bool
    is_hermitian: bool
    positive_semidefinite: bool = False
    strictly_positive: bool = False
    numerical_rank: int | None = None
    numerically_full_rank: bool = False
    numerically_singular: bool | None = None
    eigenvalues: tuple[float, ...] | None = None
    hermitian_max_deviation: float | None = None
    eigenvalue_tolerance: float | None = None
    rank_tolerance: float | None = None
    condition_number: float | None = None
    condition_number_status: str = "not_computed"
    ill_conditioned: bool = False
    tolerances: CovarianceTolerances = field(
        default_factory=CovarianceTolerances
    )
    errors: tuple[ValidationMessage, ...] = ()
    warnings: tuple[ValidationMessage, ...] = ()

    @property
    def valid(self) -> bool:
        """Whether the matrix is a covariance matrix within stated tolerances."""
        return (
            self.is_numeric
            and self.is_square
            and self.is_finite
            and self.is_hermitian
            and self.positive_semidefinite
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize all diagnostics, using null instead of infinite JSON numbers."""
        matrix_type = None
        if self.is_hermitian:
            matrix_type = (
                "real_symmetric" if self.data_kind == "real" else "complex_hermitian"
            )
        return {
            "valid": self.valid,
            "shape": list(self.shape),
            "data_kind": self.data_kind,
            "matrix_type": matrix_type,
            "is_numeric": self.is_numeric,
            "is_square": self.is_square,
            "is_finite": self.is_finite,
            "is_hermitian": self.is_hermitian,
            "positive_semidefinite": self.positive_semidefinite,
            "strictly_positive_eigenvalues": self.strictly_positive,
            "numerical_rank": self.numerical_rank,
            "numerically_full_rank": self.numerically_full_rank,
            "numerically_singular": self.numerically_singular,
            "eigenvalues": self.eigenvalues,
            "hermitian_max_deviation": self.hermitian_max_deviation,
            "eigenvalue_tolerance": self.eigenvalue_tolerance,
            "rank_tolerance": self.rank_tolerance,
            "condition_number": self.condition_number,
            "condition_number_status": self.condition_number_status,
            "ill_conditioned": self.ill_conditioned,
            "tolerances": self.tolerances.to_dict(),
            "errors": messages_to_dict(self.errors),
            "warnings": messages_to_dict(self.warnings),
        }


def _early_report(
    shape: tuple[int, ...],
    data_kind: str,
    tolerances: CovarianceTolerances,
    errors: list[ValidationMessage],
    *,
    is_numeric: bool = False,
    is_square: bool = False,
    is_finite: bool = False,
    is_hermitian: bool = False,
    hermitian_max_deviation: float | None = None,
) -> CovarianceReport:
    return CovarianceReport(
        shape=shape,
        data_kind=data_kind,
        is_numeric=is_numeric,
        is_square=is_square,
        is_finite=is_finite,
        is_hermitian=is_hermitian,
        hermitian_max_deviation=hermitian_max_deviation,
        tolerances=tolerances,
        errors=tuple(errors),
    )


def check_covariance(
    matrix: Any, *, tolerances: CovarianceTolerances | None = None
) -> CovarianceReport:
    """Check shape, finiteness, Hermitian symmetry, and positive semidefiniteness.

    Eigenvalues smaller than the PSD tolerance are accepted only within that
    explicit numerical policy. Numerical rank uses a separate threshold. A
    valid singular covariance therefore does not imply numerical invertibility.
    """
    tolerances = tolerances or CovarianceTolerances()
    errors: list[ValidationMessage] = []
    try:
        array = as_numeric_array(matrix, name="covariance")
    except ValueError as exc:
        errors.append(ValidationMessage("invalid_numeric_matrix", str(exc)))
        return _early_report((), "unknown", tolerances, errors)

    shape = tuple(array.shape)
    data_kind = "complex" if np.iscomplexobj(array) else "real"
    is_square = (
        array.ndim == 2 and array.shape[0] > 0 and array.shape[0] == array.shape[1]
    )
    if not is_square:
        errors.append(
            ValidationMessage(
                "invalid_shape",
                "covariance must be a non-empty two-dimensional square matrix",
            )
        )
        return _early_report(
            shape, data_kind, tolerances, errors, is_numeric=True
        )

    finite = bool(np.all(np.isfinite(array)))
    if not finite:
        errors.append(
            ValidationMessage("non_finite", "covariance contains NaN or infinity")
        )
        return _early_report(
            shape,
            data_kind,
            tolerances,
            errors,
            is_numeric=True,
            is_square=True,
        )

    deviation = float(np.max(np.abs(array - array.conj().T)))
    hermitian = bool(
        np.allclose(
            array,
            array.conj().T,
            rtol=tolerances.symmetry_rtol,
            atol=tolerances.symmetry_atol,
        )
    )
    if not hermitian:
        errors.append(
            ValidationMessage(
                "not_hermitian",
                "covariance is not real symmetric or complex Hermitian "
                "within tolerance",
            )
        )
        return _early_report(
            shape,
            data_kind,
            tolerances,
            errors,
            is_numeric=True,
            is_square=True,
            is_finite=True,
            hermitian_max_deviation=deviation,
        )

    try:
        eigenvalues = np.linalg.eigvalsh(array)
    except np.linalg.LinAlgError as exc:
        errors.append(ValidationMessage("eigenvalue_failure", str(exc)))
        return CovarianceReport(
            shape=shape,
            data_kind=data_kind,
            is_numeric=True,
            is_square=True,
            is_finite=True,
            is_hermitian=True,
            hermitian_max_deviation=deviation,
            condition_number_status="failed",
            tolerances=tolerances,
            errors=tuple(errors),
        )

    if not np.all(np.isfinite(eigenvalues)):
        errors.append(
            ValidationMessage(
                "non_finite_eigenvalues",
                "eigenvalue computation did not produce finite values",
            )
        )
        return CovarianceReport(
            shape=shape,
            data_kind=data_kind,
            is_numeric=True,
            is_square=True,
            is_finite=True,
            is_hermitian=True,
            hermitian_max_deviation=deviation,
            condition_number_status="failed",
            tolerances=tolerances,
            errors=tuple(errors),
        )

    absolute_eigenvalues = np.abs(eigenvalues)
    spectral_scale = float(np.max(absolute_eigenvalues))
    eigenvalue_tolerance = max(
        tolerances.eigenvalue_atol,
        tolerances.eigenvalue_rtol * spectral_scale,
    )
    rank_tolerance = max(
        tolerances.rank_atol, tolerances.rank_rtol * spectral_scale
    )
    minimum = float(np.min(eigenvalues))
    positive_semidefinite = minimum >= -eigenvalue_tolerance
    strictly_positive = minimum > 0
    numerical_rank = int(np.count_nonzero(absolute_eigenvalues > rank_tolerance))
    full_rank = numerical_rank == array.shape[0]
    smallest_absolute = float(np.min(absolute_eigenvalues))
    if smallest_absolute == 0:
        condition_number = None
        condition_status = "infinite"
        ill_conditioned = True
    else:
        with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
            raw_condition = float(
                np.divide(spectral_scale, smallest_absolute)
            )
        condition_number = raw_condition if isfinite(raw_condition) else None
        condition_status = "computed" if condition_number is not None else "overflow"
        ill_conditioned = condition_number is None or (
            condition_number > tolerances.condition_warning
        )

    if not positive_semidefinite:
        errors.append(
            ValidationMessage(
                "negative_eigenvalue",
                f"minimum eigenvalue {minimum:.6g} is below "
                f"-{eigenvalue_tolerance:.6g}",
            )
        )

    warnings: list[ValidationMessage] = []
    if minimum < 0 and positive_semidefinite:
        warnings.append(
            ValidationMessage(
                "negative_eigenvalue_tolerated",
                "a small negative eigenvalue was accepted by the PSD tolerance",
            )
        )
    if not full_rank:
        warnings.append(
            ValidationMessage(
                "numerically_singular",
                f"numerical rank {numerical_rank} is smaller than matrix "
                f"dimension {array.shape[0]}",
            )
        )
    if ill_conditioned:
        warnings.append(
            ValidationMessage(
                "ill_conditioned",
                "the covariance is singular or exceeds the condition-number "
                "warning threshold",
            )
        )

    return CovarianceReport(
        shape=shape,
        data_kind=data_kind,
        is_numeric=True,
        is_square=True,
        is_finite=True,
        is_hermitian=True,
        positive_semidefinite=positive_semidefinite,
        strictly_positive=strictly_positive,
        numerical_rank=numerical_rank,
        numerically_full_rank=full_rank,
        numerically_singular=not full_rank,
        eigenvalues=tuple(float(value) for value in eigenvalues),
        hermitian_max_deviation=deviation,
        eigenvalue_tolerance=eigenvalue_tolerance,
        rank_tolerance=rank_tolerance,
        condition_number=condition_number,
        condition_number_status=condition_status,
        ill_conditioned=ill_conditioned,
        tolerances=tolerances,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
