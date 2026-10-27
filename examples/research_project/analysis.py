"""Read synthetic inputs for the cross-host GWRC acceptance exercise."""

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def load_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    """Load the PSD and covariance documents without transforming either one."""
    psd = json.loads((ROOT / "data" / "psd.json").read_text(encoding="utf-8"))
    covariance = json.loads(
        (ROOT / "data" / "covariance.json").read_text(encoding="utf-8")
    )
    return psd, covariance


def main() -> int:
    """Print declarations and dimensions; no detector model is inferred."""
    psd, covariance = load_inputs()
    matrix = covariance["matrix"]
    print(f"Data origin: {psd['data_origin']}")
    print(f"PSD convention: {psd['spectral_convention']}")
    print(f"Frequency points: {len(psd['frequency'])}")
    print(f"Covariance shape: {len(matrix)} x {len(matrix[0])}")
    print("No sidedness conversion or independence assumption is applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
