"""Small result types shared by scientific checkers."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationMessage:
    """A machine-readable validation finding."""

    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {"code": self.code, "message": self.message}


def messages_to_dict(
    messages: tuple[ValidationMessage, ...],
) -> list[dict[str, Any]]:
    """Serialize validation findings without losing their stable codes."""
    return [message.to_dict() for message in messages]
