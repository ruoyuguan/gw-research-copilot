"""The host-independent GWRC command-line interface."""

import argparse
import json
import math
import shutil
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from gwrc import __version__
from gwrc.core.errors import GWRCError, InputError
from gwrc.core.json_utils import json_text
from gwrc.integrations.arc import ArcPaperClient, probe_arc
from gwrc.reporting.run import RunRecorder, distribution_version
from gwrc.tools.covariance import CovarianceTolerances, check_covariance
from gwrc.tools.fisher import fisher_demo
from gwrc.tools.psd import PSDTolerances, check_psd


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("JSON numbers must be finite")
    return number


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON numeric constant: {value}")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_float=_finite_float,
            parse_constant=_reject_constant,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise InputError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise InputError("input JSON must be an object")
    return payload


def _required(payload: dict[str, Any], key: str) -> Any:
    if key not in payload:
        raise InputError(f"input JSON requires the {key!r} field")
    return payload[key]


def _recorded(
    *,
    tool: str,
    output_dir: Path | None,
    input_data: Any,
    parameters: dict[str, Any],
    input_files: list[Path],
    operation: Callable[[], tuple[dict[str, Any], bool]],
) -> int:
    recorder = RunRecorder(
        tool=tool,
        output_dir=output_dir,
        input_data=input_data,
        parameters=parameters,
        input_files=input_files,
    )
    try:
        result, passed = operation()
    except GWRCError as exc:
        recorder.fail(exc)
        raise
    recorder.complete(result)
    sys.stdout.write(json_text(result))
    print(f"Run record: {recorder.directory / 'run.json'}", file=sys.stderr)
    print(f"Markdown report: {recorder.directory / 'report.md'}", file=sys.stderr)
    return 0 if passed else 1


def _covariance_tolerances(args: argparse.Namespace) -> CovarianceTolerances:
    try:
        return CovarianceTolerances(
            symmetry_rtol=args.symmetry_rtol,
            symmetry_atol=args.symmetry_atol,
            eigenvalue_rtol=args.eigenvalue_rtol,
            eigenvalue_atol=args.eigenvalue_atol,
            rank_rtol=args.rank_rtol,
            rank_atol=args.rank_atol,
            condition_warning=args.condition_warning,
        )
    except ValueError as exc:
        raise InputError(f"invalid covariance tolerance: {exc}") from exc


def _check_covariance(args: argparse.Namespace) -> int:
    payload = _read_json(args.input)
    tolerances = _covariance_tolerances(args)

    def operation() -> tuple[dict[str, Any], bool]:
        report = check_covariance(
            _required(payload, "matrix"), tolerances=tolerances
        )
        result = report.to_dict()
        return result, report.valid

    return _recorded(
        tool="check-cov",
        output_dir=args.output_dir,
        input_data=payload,
        parameters={
            "definition": (
                "finite real-symmetric or complex-Hermitian "
                "positive semidefinite matrix"
            ),
            "tolerances": tolerances.to_dict(),
        },
        input_files=[args.input],
        operation=operation,
    )


def _check_psd(args: argparse.Namespace) -> int:
    payload = _read_json(args.input)
    _required(payload, "frequency")
    _required(payload, "psd")
    expected_order = args.order or payload.get("frequency_order", "increasing")
    if expected_order not in ("increasing", "decreasing", "unordered"):
        raise InputError(
            "frequency_order must be increasing, decreasing, or unordered"
        )
    try:
        tolerances = PSDTolerances(atol=args.psd_atol, rtol=args.psd_rtol)
    except ValueError as exc:
        raise InputError(f"invalid PSD tolerance: {exc}") from exc

    def operation() -> tuple[dict[str, Any], bool]:
        report = check_psd(
            payload["frequency"],
            payload["psd"],
            frequency_unit=payload.get("frequency_unit"),
            psd_unit=payload.get("psd_unit"),
            psd_definition=payload.get("psd_definition"),
            spectral_convention=payload.get("spectral_convention"),
            fourier_convention=payload.get("fourier_convention"),
            expected_order=expected_order,
            tolerances=tolerances,
        )
        result = report.to_dict()
        return result, report.valid

    return _recorded(
        tool="check-psd",
        output_dir=args.output_dir,
        input_data=payload,
        parameters={
            "spectrum_kind": "real auto-spectrum",
            "expected_frequency_order": expected_order,
            "tolerances": tolerances.to_dict(),
            "convention_conversion": "none",
        },
        input_files=[args.input],
        operation=operation,
    )


def _fisher_demo(args: argparse.Namespace) -> int:
    def operation() -> tuple[dict[str, Any], bool]:
        try:
            demo = fisher_demo(rtol=args.reference_rtol, atol=args.reference_atol)
        except ValueError as exc:
            raise InputError(f"invalid Fisher reference tolerance: {exc}") from exc
        return demo.to_dict(), demo.matches_analytic

    return _recorded(
        tool="fisher-demo",
        output_dir=args.output_dir,
        input_data={"data_origin": "synthetic", "example": "gaussian_mean_2d_v1"},
        parameters={
            "model": "real Gaussian linear mean, fixed positive-definite covariance",
            "definition": "F = J^T C^-1 J",
            "reference_rtol": args.reference_rtol,
            "reference_atol": args.reference_atol,
        },
        input_files=[],
        operation=operation,
    )


def _arc_metadata(args: argparse.Namespace) -> int:
    paper_id = args.paper_id.strip()
    if not paper_id:
        raise InputError("paper_id must not be empty")

    def operation() -> tuple[dict[str, Any], bool]:
        try:
            client = ArcPaperClient(timeout=args.timeout)
        except ValueError as exc:
            raise InputError(str(exc)) from exc
        return client.get_metadata(paper_id), True

    return _recorded(
        tool="arc-metadata",
        output_dir=args.output_dir,
        input_data={"paper_id": paper_id},
        parameters={"operation": "get-metadata", "timeout_seconds": args.timeout},
        input_files=[],
        operation=operation,
    )


def _package_check(name: str, *, required: bool) -> dict[str, Any]:
    installed = distribution_version(name)
    state = "available" if installed else ("failed" if required else "not_configured")
    return {
        "name": name,
        "state": state,
        "required": required,
        "version": installed,
    }


def _doctor(args: argparse.Namespace) -> int:
    python_ok = sys.version_info >= (3, 11)
    checks: list[dict[str, Any]] = [
        {
            "name": "Python",
            "state": "available" if python_ok else "failed",
            "required": True,
            "version": sys.version.split()[0],
            "detail": "Python 3.11 or newer is required",
        },
        {
            "name": "gw-research-copilot",
            "state": "available",
            "required": True,
            "version": __version__,
        },
        _package_check("numpy", required=True),
        _package_check("scipy", required=True),
        _package_check("sympy", required=False),
        {
            "name": "git",
            "state": "available" if shutil.which("git") else "not_configured",
            "required": False,
            "detail": "used for optional working-directory commit provenance",
        },
    ]
    arc = probe_arc().to_dict()
    arc["name"] = "ARC arc-paper"
    arc["required"] = False
    checks.append(arc)
    skill_root = Path.cwd() / ".agents" / "skills"
    expected_skills = {"gw-literature", "gw-theory", "gw-statistics", "gw-review"}
    found = sorted(
        path.parent.name for path in skill_root.glob("*/SKILL.md")
    )
    skills_present = set(found) == expected_skills
    checks.append(
        {
            "name": "project-skills",
            "state": "present" if skills_present else "not_found",
            "required": False,
            "skills": found,
            "detail": (
                "static file discovery from the current directory; "
                "not a live host test"
            ),
        }
    )
    healthy = all(
        check["state"] != "failed" for check in checks
    ) and python_ok
    document = {"healthy": healthy, "checks": checks}
    if args.json:
        sys.stdout.write(json_text(document))
    else:
        print(f"GWRC doctor: {'healthy' if healthy else 'failed'}")
        for check in checks:
            version_text = f" ({check['version']})" if check.get("version") else ""
            print(f"- {check['name']}: {check['state']}{version_text}")
            if check.get("detail"):
                print(f"  {check['detail']}")
    return 0 if healthy else 1


def _output_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "new directory for run.json and report.md "
            "(default: a unique runs/ directory)"
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    """Construct the public command grammar without executing scientific tools."""
    parser = argparse.ArgumentParser(
        prog="gwrc",
        description=(
            "Deterministic gravitational-wave research checks with "
            "reproducible records. Numerical success does not validate a "
            "physical model."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    commands = parser.add_subparsers(dest="command")

    doctor = commands.add_parser(
        "doctor", help="inspect local and optional dependencies"
    )
    doctor.add_argument(
        "--json", action="store_true", help="emit machine-readable diagnostics"
    )
    doctor.set_defaults(handler=_doctor)

    covariance = commands.add_parser(
        "check-cov", help="check a covariance JSON matrix"
    )
    covariance.add_argument(
        "input", type=Path, help="JSON object containing matrix"
    )
    _output_argument(covariance)
    defaults = CovarianceTolerances()
    for name in (
        "symmetry_rtol",
        "symmetry_atol",
        "eigenvalue_rtol",
        "eigenvalue_atol",
        "rank_rtol",
        "rank_atol",
        "condition_warning",
    ):
        covariance.add_argument(
            "--" + name.replace("_", "-"),
            type=float,
            default=getattr(defaults, name),
            dest=name,
        )
    covariance.set_defaults(handler=_check_covariance)

    psd = commands.add_parser(
        "check-psd", help="check a real auto-spectrum JSON input"
    )
    psd.add_argument(
        "input",
        type=Path,
        help="JSON frequency/PSD object with declarations",
    )
    _output_argument(psd)
    psd.add_argument(
        "--order",
        choices=("increasing", "decreasing", "unordered"),
        help="override the JSON frequency_order declaration (default: increasing)",
    )
    psd.add_argument("--psd-atol", type=float, default=0.0)
    psd.add_argument("--psd-rtol", type=float, default=0.0)
    psd.set_defaults(handler=_check_psd)

    fisher = commands.add_parser(
        "fisher-demo",
        help="compare a synthetic Gaussian Fisher matrix with its analytic result",
    )
    _output_argument(fisher)
    fisher.add_argument("--reference-rtol", type=float, default=1e-12)
    fisher.add_argument("--reference-atol", type=float, default=1e-12)
    fisher.set_defaults(handler=_fisher_demo)

    arc = commands.add_parser(
        "arc-metadata", help="retrieve paper metadata through an installed ARC CLI"
    )
    arc.add_argument(
        "paper_id",
        help="arXiv, INSPIRE, DOI, or other ARC paper identifier",
    )
    _output_argument(arc)
    arc.add_argument("--timeout", type=float, default=60.0)
    arc.set_defaults(handler=_arc_metadata)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return its documented process exit code."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    try:
        return handler(args)
    except GWRCError as exc:
        print(f"gwrc: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
