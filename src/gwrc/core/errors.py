"""Exceptions with stable command-line exit semantics."""


class GWRCError(Exception):
    """Base class for expected GWRC failures."""

    exit_code = 1


class InputError(GWRCError):
    """Raised when an input document or command argument is malformed."""

    exit_code = 2


class ModelError(GWRCError):
    """Raised when assumptions of a scientific model are not satisfied."""


class IntegrationError(GWRCError):
    """Raised when an optional external service cannot complete a request."""
