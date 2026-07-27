"""Pydantic schemas for standard API request and response structures."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue


def to_camel(value: str) -> str:
    """Convert a Python snake_case identifier to a camelCase wire name."""

    parts = value.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def to_snake(value: str) -> str:
    """Convert a camelCase or PascalCase identifier to snake_case."""

    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()


class ApiModel(BaseModel):
    """Readable Python model with backward-compatible camelCase JSON aliases."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ApiError(ApiModel):
    status: Literal["error"] = Field(
        default="error", description="Indicates the response status is an error"
    )
    message: str = Field(..., description="A user-friendly message describing the error")
    code: str | None = Field(None, description="An optional error code for API clients")
    details: JsonValue | None = Field(
        None, description="Optional structured details about the error"
    )
    request_id: str = Field(
        default="", description="Request identifier used to correlate server logs"
    )


class ApiSuccess[T](ApiModel):
    status: Literal["success"] = Field(
        default="success", description="Indicates the response status is a success"
    )
    data: T | None = Field(None, description="The payload of the response")


class ApiMessage(ApiModel):
    status: Literal["success"] = Field(
        default="success", description="Indicates the response status is a success"
    )
    message: str = Field(..., description="A status message")


class PaginatedResponse[T](BaseModel):
    status: str = Field(default="success", description="Indicates the response status is a success")
    data: list[T] = Field(..., description="List of items in the current page")
    page: int = Field(..., description="Current page number (1-indexed)")
    per_page: int = Field(..., description="Number of items per page")
    total: int = Field(..., description="Total number of items available")
    total_pages: int = Field(..., description="Total number of pages")


class CursorPage[T](ApiModel):
    """Standard cursor-based collection response for new APIs."""

    items: list[T] = Field(default_factory=list)
    next_cursor: str | None = None
    total: int | None = None


__all__ = [
    "ApiError",
    "ApiMessage",
    "ApiModel",
    "ApiSuccess",
    "CursorPage",
    "PaginatedResponse",
    "to_camel",
    "to_snake",
]
