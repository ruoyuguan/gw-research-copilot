"""Scientific boundary tests for covariance diagnostics."""

import numpy as np
import pytest

from gwrc.core.json_utils import json_text
from gwrc.tools.covariance import CovarianceTolerances, check_covariance


def test_real_positive_definite_covariance() -> None:
    report = check_covariance([[2.0, 0.3], [0.3, 1.0]])

    assert report.valid
    assert report.strictly_positive
    assert report.numerically_full_rank
    assert report.numerical_rank == 2
    expected = ((3.0 - np.sqrt(1.36)) / 2, (3.0 + np.sqrt(1.36)) / 2)
    assert report.eigenvalues == pytest.approx(expected)
    assert report.condition_number == pytest.approx(expected[1] / expected[0])
    assert not report.errors


def test_complex_hermitian_covariance() -> None:
    report = check_covariance([[2.0, 1.0 + 2.0j], [1.0 - 2.0j, 6.0]])

    assert report.valid
    assert report.data_kind == "complex"
    assert report.to_dict()["matrix_type"] == "complex_hermitian"
    assert report.eigenvalues[0] > 0


def test_singular_positive_semidefinite_is_not_invertible() -> None:
    report = check_covariance([[1.0, 1.0], [1.0, 1.0]])

    assert report.valid
    assert report.positive_semidefinite
    assert not report.strictly_positive
    assert report.numerically_singular
    assert not report.numerically_full_rank
    assert report.condition_number is None
    assert report.condition_number_status == "infinite"
    assert "numerically_singular" in {item.code for item in report.warnings}


def test_zero_matrix_is_valid_psd_but_singular() -> None:
    report = check_covariance(np.zeros((2, 2)))

    assert report.valid
    assert report.numerical_rank == 0
    assert report.eigenvalues == (0.0, 0.0)
    assert report.ill_conditioned
    assert json_text(report.to_dict())


def test_negative_eigenvalue_is_invalid() -> None:
    report = check_covariance(np.diag([1.0, -0.01]))

    assert not report.valid
    assert "negative_eigenvalue" in {item.code for item in report.errors}


def test_small_negative_eigenvalue_requires_explicit_tolerance() -> None:
    report = check_covariance(np.diag([1.0, -1e-12]))

    assert report.valid
    assert not report.strictly_positive
    assert "negative_eigenvalue_tolerated" in {
        item.code for item in report.warnings
    }


def test_non_symmetric_matrix_is_rejected() -> None:
    report = check_covariance([[1.0, 2.0], [0.0, 1.0]])

    assert not report.valid
    assert report.eigenvalues is None
    assert "not_hermitian" in {item.code for item in report.errors}


def test_non_hermitian_complex_matrix_is_rejected() -> None:
    report = check_covariance([[1.0, 1.0j], [1.0j, 1.0]])

    assert not report.valid
    assert "not_hermitian" in {item.code for item in report.errors}


@pytest.mark.parametrize("bad_value", [np.nan, np.inf, -np.inf])
def test_non_finite_covariance_is_rejected(bad_value: float) -> None:
    report = check_covariance([[1.0, bad_value], [bad_value, 1.0]])

    assert not report.valid
    assert not report.is_finite
    assert report.eigenvalues is None
    assert "non_finite" in {item.code for item in report.errors}


@pytest.mark.parametrize("matrix", [[], [1.0, 2.0], [[1.0, 2.0, 3.0]]])
def test_invalid_shapes_are_rejected(matrix: object) -> None:
    report = check_covariance(matrix)

    assert not report.valid
    assert "invalid_shape" in {item.code for item in report.errors}


def test_text_matrix_is_rejected_without_crashing() -> None:
    report = check_covariance([["not", "numeric"], ["numeric", "here"]])

    assert not report.valid
    assert "invalid_numeric_matrix" in {item.code for item in report.errors}


def test_conditioning_and_numerical_rank_are_distinct() -> None:
    report = check_covariance(np.diag([1.0, 1e-14]))

    assert report.valid
    assert report.strictly_positive
    assert report.numerically_singular
    assert report.condition_number == pytest.approx(1e14)
    assert report.ill_conditioned


def test_condition_number_overflow_has_a_safe_json_representation() -> None:
    report = check_covariance(np.diag([1.0, 1e-320]))

    assert report.condition_number is None
    assert report.condition_number_status == "overflow"
    assert report.ill_conditioned
    assert "inf" not in json_text(report.to_dict())


def test_invalid_tolerances_are_rejected() -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        CovarianceTolerances(rank_atol=-1.0)
    with pytest.raises(ValueError, match="positive"):
        CovarianceTolerances(condition_warning=0.0)
