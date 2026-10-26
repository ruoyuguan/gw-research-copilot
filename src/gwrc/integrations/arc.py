"""Minimal adapter for ARC's documented arc-paper command-line interface."""

import json
import math
import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from gwrc.core.errors import IntegrationError


@dataclass(frozen=True)
class ARCStatus:
    """Observed optional ARC availability, never an assumed integration state."""

    state: Literal["not_configured", "available", "failed"]
    detail: str
    command: tuple[str, ...] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the status for doctor output."""
        return {
            "state": self.state,
            "optional": True,
            "detail": self.detail,
            "command": self.command,
            "network_verified": False,
        }


def _arc_command(environment: Mapping[str, str]) -> tuple[str, ...] | None:
    configured = environment.get("GWRC_ARC_PAPER")
    if configured:
        path = Path(configured).expanduser()
        if not path.is_file():
            raise IntegrationError(
                "GWRC_ARC_PAPER does not point to an arc-paper executable: "
                f"{configured}"
            )
        return (str(path),)
    discovered = shutil.which("arc-paper")
    return (discovered,) if discovered else None


class ArcPaperClient:
    """Call a separately installed ARC paper CLI with bounded subprocesses."""

    def __init__(
        self,
        command: Sequence[str] | None = None,
        *,
        timeout: float = 60.0,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        """Resolve an explicit command or the GWRC_ARC_PAPER/PATH installation."""
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("ARC timeout must be finite and positive")
        self.timeout = timeout
        self.environment = os.environ if environment is None else environment
        self.command = (
            tuple(command)
            if command is not None
            else _arc_command(self.environment)
        )

    def _run(self, arguments: Sequence[str], timeout: float) -> str:
        if self.command is None:
            raise IntegrationError(
                "ARC is not configured. Install arc-paper separately or set "
                "GWRC_ARC_PAPER to its executable; local scientific tools "
                "remain available."
            )
        try:
            completed = subprocess.run(
                [*self.command, *arguments],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise IntegrationError(
                f"arc-paper exceeded the {timeout:g}-second timeout"
            ) from exc
        except OSError as exc:
            raise IntegrationError(f"cannot execute arc-paper: {exc}") from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise IntegrationError(
                f"arc-paper exited with code {completed.returncode}: {detail[:2000]}"
            )
        return completed.stdout

    def probe(self) -> ARCStatus:
        """Check only local CLI readiness; do not make a paper-network request."""
        if self.command is None:
            return ARCStatus(
                "not_configured",
                "ARC is optional and arc-paper was not found; "
                "local tools are available",
            )
        try:
            output = self._run(("--help",), min(self.timeout, 15.0))
        except IntegrationError as exc:
            return ARCStatus("failed", str(exc), self.command)
        if "usage" not in output.lower():
            return ARCStatus(
                "failed",
                "arc-paper --help returned an unrecognized output contract",
                self.command,
            )
        return ARCStatus(
            "available",
            "arc-paper --help succeeded; paper-network access is not tested by doctor",
            self.command,
        )

    def get_metadata(self, paper_id: str) -> dict[str, Any]:
        """Retrieve real ARC metadata and validate its typed JSON envelope."""
        if not paper_id.strip():
            raise IntegrationError("paper_id must not be empty")
        output = self._run(("get-metadata", paper_id), self.timeout)
        try:
            response = json.loads(output)
        except json.JSONDecodeError as exc:
            raise IntegrationError("arc-paper returned invalid JSON") from exc
        if not isinstance(response, dict) or not isinstance(
            response.get("status"), str
        ):
            raise IntegrationError("arc-paper response lacks a typed status envelope")
        if response.get("schema_version") != "ac.command_result.v2":
            raise IntegrationError(
                "unsupported ARC command-result schema: "
                + json_text_for_error(response)
            )
        if (
            response["status"] != "completed"
            or response.get("error") is not None
            or not isinstance(response.get("data"), dict)
        ):
            raise IntegrationError(
                "ARC metadata request was not successful: "
                + json_text_for_error(response)
            )
        return {
            "paper_id": paper_id,
            "backend": "ARC arc-paper public CLI",
            "arc_response": response,
            "retrieval_completed": True,
            "scientific_validation": "metadata retrieval only; not a literature review",
        }


def json_text_for_error(response: dict[str, Any]) -> str:
    """Keep a bounded upstream error envelope for actionable diagnostics."""
    try:
        text = json.dumps(response, ensure_ascii=False)
    except (TypeError, ValueError):
        text = str(response)
    return text[:2000]


def probe_arc(
    *, environment: Mapping[str, str] | None = None
) -> ARCStatus:
    """Report missing, working, and broken optional ARC installations distinctly."""
    try:
        return ArcPaperClient(environment=environment).probe()
    except IntegrationError as exc:
        return ARCStatus("failed", str(exc))
