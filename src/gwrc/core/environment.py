"""Lightweight environment inspection used by non-scientific CLI commands."""

from importlib.metadata import PackageNotFoundError, version


def distribution_version(name: str) -> str | None:
    """Return an installed distribution version without importing the package."""
    try:
        return version(name)
    except PackageNotFoundError:
        return None
