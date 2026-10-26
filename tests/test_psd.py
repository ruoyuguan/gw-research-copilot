"""Auto-spectrum validation tests with explicit spectral conventions."""

from typing import Any

import numpy as np
import pytest

from gwrc.tools.psd import PSDTolerances, check_psd


def declarations(convention: str = "one-sided") -> dict[str, str]:
    return {
        "frequency_unit": "Hz",
        "psd_unit": "synthetic_amplitude^2/Hz",
        "psd_definition": "Synthetic tabulated auto-spectrum; no conversion applied",
        "spectral_convention": convention,
        "fourier_convention": "No Fourier transform is performed by this test",
    }


def test_valid_one_sided_psd() -> None:
    report = check_psd([0.0, 1.0, 2.0], [1.0, 1.5, 0.5], **declarations())

    assert report.valid
    assert report.frequency_order_matches
    assert report.minimum_psd == 0.5
    assert report.to_dict()["spectrum_kind"] == "auto"


def test_valid_two_sided_psd_allows_negative_frequency() -> None:
    report = check_psd(
        [-1.0, 0.0, 1.0], [1.0, 2.0, 1.0], **declarations("two-sided")
    )

    assert report.valid
    assert report.frequency_convention_consistent


def test_descending_frequency_order() -> None:
    report = check_psd(
        [2.0, 1.0, 0.0], [0.5, 1.5, 1.0], expected_order="decreasing", **declarations()
    )

    assert report.valid


def test_unordered_still_requires_unique_finite_values() -> None:
    report = check_psd(
        [0.0, 2.0, 1.0], [1.0, 0.5, 1.5], expected_order="unordered", **declarations()
    )

    assert report.valid
    assert report.frequency_order_matches is None


def test_mismatched_shapes_are_rejected() -> None:
    report = check_psd([0.0, 1.0, 2.0], [1.0, 2.0], **declarations())

    assert not report.valid
    assert "shape_mismatch" in {item.code for item in report.errors}


def test_complex_auto_spectrum_is_not_silently_coerced_to_real() -> None:
    report = check_psd([0.0, 1.0], np.array([1.0 + 0.0j, 2.0 + 0.0j]), **declarations())

    assert not report.valid
    assert "complex_auto_spectrum" in {item.code for item in report.errors}


@pytest.mark.parametrize(
    ("frequency", "psd"),
    [([0.0, np.nan], [1.0, 2.0]), ([0.0, 1.0], [1.0, np.inf])],
)
def test_non_finite_values_are_rejected(frequency: Any, psd: Any) -> None:
    report = check_psd(frequency, psd, **declarations())

    assert not report.valid
    assert "non_finite" in {item.code for item in report.errors}


def test_negative_psd_is_rejected_by_default() -> None:
    report = check_psd([0.0, 1.0], [1.0, -1e-3], **declarations())

    assert not report.valid
    assert "negative_psd" in {item.code for item in report.errors}


def test_negative_psd_tolerance_is_reported() -> None:
    report = check_psd(
        [0.0, 1.0],
        [1.0, -1e-3],
        tolerances=PSDTolerances(atol=1e-2),
        **declarations(),
    )

    assert report.valid
    assert "negative_psd_tolerated" in {item.code for item in report.warnings}


def test_zero_psd_is_allowed() -> None:
    report = check_psd([0.0, 1.0], [0.0, 0.0], **declarations())

    assert report.valid


def test_duplicate_frequency_is_rejected() -> None:
    report = check_psd([0.0, 1.0, 1.0], [1.0, 2.0, 3.0], **declarations())

    assert not report.valid
    assert "duplicate_frequency" in {item.code for item in report.errors}


def test_unsorted_frequency_is_rejected() -> None:
    report = check_psd([0.0, 2.0, 1.0], [1.0, 2.0, 3.0], **declarations())

    assert not report.valid
    assert "frequency_order" in {item.code for item in report.errors}


def test_one_sided_negative_frequency_is_rejected() -> None:
    report = check_psd([-1.0, 0.0, 1.0], [1.0, 2.0, 1.0], **declarations())

    assert not report.valid
    assert "negative_one_sided_frequency" in {item.code for item in report.errors}


@pytest.mark.parametrize(
    "key", ["frequency_unit", "psd_unit", "psd_definition", "spectral_convention"]
)
def test_required_declarations_cannot_be_omitted(key: str) -> None:
    metadata = declarations()
    metadata[key] = ""
    report = check_psd([0.0, 1.0], [1.0, 2.0], **metadata)

    assert not report.valid
    assert not report.metadata_complete
    assert "missing_declarations" in {item.code for item in report.errors}


def test_unknown_spectral_convention_is_rejected() -> None:
    report = check_psd([0.0, 1.0], [1.0, 2.0], **declarations("unspecified"))

    assert not report.valid
    assert "invalid_spectral_convention" in {item.code for item in report.errors}


def test_empty_fourier_declaration_is_rejected_when_supplied() -> None:
    metadata = declarations()
    metadata["fourier_convention"] = ""
    report = check_psd([0.0, 1.0], [1.0, 2.0], **metadata)

    assert not report.valid
    assert not report.metadata_complete


def test_non_numeric_frequency_is_reported() -> None:
    report = check_psd("not-an-array", [1.0], **declarations())

    assert not report.valid
    assert "invalid_frequency" in {item.code for item in report.errors}
