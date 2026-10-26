"""Fisher information for a real Gaussian linear mean model."""

from dataclasses import dataclass
from math import isfinite
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import cho_factor, cho_solve

from gwrc.core.errors import ModelError
from gwrc.core.numeric import as_numeric_array
from gwrc.core.results import ValidationMessage, messages_to_dict
from gwrc.tools.covariance import (
    CovarianceReport,
    CovarianceTolerances,
    check_covariance,
)


@dataclass(frozen=True)
class FisherResult:
    """A Fisher matrix and the numerical evidence used to compute it."""

    jacobian: NDArray[np.float64]
    covariance: NDArray[np.float64]
    fisher_matrix: NDArray[np.float64]
    covariance_report: CovarianceReport
    warnings: tuple[ValidationMessage, ...]
    solver: str = "scipy.linalg.cho_factor/cho_solve"
    model: str = "real_gaussian_linear_mean_fixed_covariance"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the result, model dimensions, and covariance diagnostics."""
        return {
            "model": self.model,
            "definition": "F = J^T C^-1 J",
            "jacobian_shape": list(self.jacobian.shape),
            "covariance_shape": list(self.covariance.shape),
            "fisher_shape": list(self.fisher_matrix.shape),
            "jacobian": self.jacobian,
            "covariance": self.covariance,
            "fisher_matrix": self.fisher_matrix,
            "solver": self.solver,
            "covariance_report": self.covariance_report.to_dict(),
            "warnings": messages_to_dict(self.warnings),
            "assumptions": [
                "data are real and Gaussian",
                "the mean is linear in the parameters with Jacobian J",
                "C is real symmetric positive definite and parameter-independent",
            ],
            "scope_limitations": [
                "no parameter-dependent covariance derivative term",
                "no complex or multi-channel frequency-domain likelihood",
                "no gravitational-wave detector response or A/E/T channel model",
            ],
        }


@dataclass(frozen=True)
class FisherDemoResult:
    """A synthetic Fisher calculation compared with its analytic reference."""

    calculation: FisherResult
    analytic_fisher: NDArray[np.float64]
    max_absolute_error: float
    matches_analytic: bool
    rtol: float
    atol: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize the calculation and independent analytic comparison."""
        return {
            "data_origin": "synthetic",
            "description": (
                "Synthetic two-parameter Gaussian mean-model example; "
                "not LISA, TianQin, or observational data."
            ),
            "calculation": self.calculation.to_dict(),
            "analytic_fisher": self.analytic_fisher,
            "max_absolute_error": self.max_absolute_error,
            "matches_analytic": self.matches_analytic,
            "reference_comparison": {"rtol": self.rtol, "atol": self.atol},
        }


def fisher_gaussian_mean(
    jacobian: Any,
    covariance: Any,
    *,
    covariance_tolerances: CovarianceTolerances | None = None,
    condition_limit: float | None = 1e12,
) -> FisherResult:
    """Compute ``J.T @ solve(C, J)`` by a Cholesky solve, not inversion.

    The model is ``y ~ N(J theta, C)`` for real data and a fixed covariance.
    Invalid, singular, or excessively ill-conditioned covariance inputs raise
    ``ModelError`` rather than being silently regularized or pseudo-inverted.
    """
    if condition_limit is not None and (
        not isfinite(condition_limit) or condition_limit <= 0
    ):
        raise ValueError("condition_limit must be positive, finite, or None")
    try:
        jacobian_array = as_numeric_array(jacobian, name="jacobian")
        covariance_array = as_numeric_array(covariance, name="covariance")
    except ValueError as exc:
        raise ModelError(str(exc)) from exc
    if np.iscomplexobj(jacobian_array) or np.iscomplexobj(covariance_array):
        raise ModelError("this Fisher model accepts only explicitly real arrays")
    if (
        jacobian_array.ndim != 2
        or jacobian_array.shape[0] == 0
        or jacobian_array.shape[1] == 0
    ):
        raise ModelError("jacobian must be a non-empty n_by_p matrix")
    if not np.all(np.isfinite(jacobian_array)):
        raise ModelError("jacobian contains NaN or infinity")
    if covariance_array.shape != (jacobian_array.shape[0],) * 2:
        raise ModelError("covariance shape must be (n, n), matching Jacobian rows")

    covariance_report = check_covariance(
        covariance_array, tolerances=covariance_tolerances
    )
    if not covariance_report.valid:
        details = "; ".join(item.message for item in covariance_report.errors)
        raise ModelError(f"invalid fixed Gaussian covariance: {details}")
    if not covariance_report.strictly_positive:
        raise ModelError("Fisher covariance must have strictly positive eigenvalues")
    if not covariance_report.numerically_full_rank:
        raise ModelError("Fisher covariance is numerically singular")
    if (
        covariance_report.condition_number is None
        or (
            condition_limit is not None
            and covariance_report.condition_number > condition_limit
        )
    ):
        raise ModelError("Fisher covariance exceeds the conditioning limit")

    try:
        factor = cho_factor(covariance_array, lower=True, check_finite=True)
        solved = cho_solve(factor, jacobian_array, check_finite=True)
    except np.linalg.LinAlgError as exc:
        raise ModelError(f"Cholesky solve failed: {exc}") from exc
    fisher_matrix = jacobian_array.T @ solved
    fisher_matrix = 0.5 * (fisher_matrix + fisher_matrix.T)
    return FisherResult(
        jacobian=jacobian_array,
        covariance=covariance_array,
        fisher_matrix=fisher_matrix,
        covariance_report=covariance_report,
        warnings=covariance_report.warnings,
    )


def fisher_demo(*, rtol: float = 1e-12, atol: float = 1e-12) -> FisherDemoResult:
    """Run the documented synthetic example with an analytic Fisher matrix."""
    if not isfinite(rtol) or not isfinite(atol) or rtol < 0 or atol < 0:
        raise ValueError("Fisher reference tolerances must be finite and non-negative")
    jacobian = np.array([[1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    covariance = np.diag([4.0, 1.0, 1.0])
    analytic_fisher = np.array([[1.25, 1.0], [1.0, 2.0]])
    calculation = fisher_gaussian_mean(jacobian, covariance)
    error = float(np.max(np.abs(calculation.fisher_matrix - analytic_fisher)))
    return FisherDemoResult(
        calculation=calculation,
        analytic_fisher=analytic_fisher,
        max_absolute_error=error,
        matches_analytic=bool(
            np.allclose(
                calculation.fisher_matrix, analytic_fisher, rtol=rtol, atol=atol
            )
        ),
        rtol=rtol,
        atol=atol,
    )
