"""Analytic and numerical-stability tests for the Gaussian Fisher model."""

import numpy as np
import pytest

import gwrc.tools.fisher as fisher_module
from gwrc.core.errors import ModelError
from gwrc.tools.fisher import fisher_demo, fisher_gaussian_mean


def test_fisher_matches_analytic_reference() -> None:
    jacobian = np.array([[1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    covariance = np.diag([4.0, 1.0, 1.0])

    result = fisher_gaussian_mean(jacobian, covariance)

    np.testing.assert_allclose(
        result.fisher_matrix, [[1.25, 1.0], [1.0, 2.0]], rtol=1e-13, atol=1e-13
    )
    assert result.fisher_matrix.shape == (2, 2)
    assert result.covariance_report.valid


def test_cholesky_solve_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    original = fisher_module.cho_solve

    def observed_solve(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(fisher_module, "cho_solve", observed_solve)
    fisher_gaussian_mean([[1.0], [1.0]], np.eye(2))

    assert calls == [True]


def test_singular_covariance_is_not_pseudo_inverted() -> None:
    with pytest.raises(ModelError, match="strictly positive|singular"):
        fisher_gaussian_mean([[1.0], [1.0]], [[1.0, 1.0], [1.0, 1.0]])


def test_indefinite_covariance_is_rejected() -> None:
    with pytest.raises(ModelError, match="invalid fixed Gaussian covariance"):
        fisher_gaussian_mean([[1.0], [1.0]], np.diag([1.0, -1.0]))


def test_non_symmetric_covariance_is_rejected() -> None:
    with pytest.raises(ModelError, match="invalid fixed Gaussian covariance"):
        fisher_gaussian_mean([[1.0], [1.0]], [[1.0, 1.0], [0.0, 1.0]])


def test_complex_model_is_outside_scope() -> None:
    with pytest.raises(ModelError, match="only explicitly real"):
        fisher_gaussian_mean(np.array([[1.0 + 0.0j]]), np.eye(1))


def test_shape_and_finite_checks() -> None:
    with pytest.raises(ModelError, match="matching Jacobian rows"):
        fisher_gaussian_mean([[1.0], [1.0]], np.eye(3))
    with pytest.raises(ModelError, match="NaN or infinity"):
        fisher_gaussian_mean([[np.nan]], np.eye(1))


def test_ill_conditioned_covariance_is_rejected() -> None:
    with pytest.raises(ModelError, match="singular|conditioning"):
        fisher_gaussian_mean([[1.0], [1.0]], np.diag([1.0, 1e-14]))


def test_demo_is_synthetic_and_matches_reference() -> None:
    result = fisher_demo()
    document = result.to_dict()

    assert result.matches_analytic
    assert result.max_absolute_error < 1e-12
    assert document["data_origin"] == "synthetic"
    assert "not LISA" in document["description"]
    np.testing.assert_array_equal(
        document["analytic_fisher"], [[1.25, 1.0], [1.0, 2.0]]
    )
