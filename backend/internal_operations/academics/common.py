"""Small transport helpers shared by system-admin academic routes."""

from __future__ import annotations

from typing import Any


def model_payload(model) -> dict[str, Any]:
    """Return only explicitly meaningful Pydantic fields for a use case."""

    return model.model_dump(exclude_none=True)
