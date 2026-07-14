"""Pydantic schemas for standard API request and response structures."""

from typing import Generic, TypeVar, Optional, Any, List
from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiError(BaseModel):
    status: str = Field(
        default="error", description="Indicates the response status is an error"
    )
    message: str = Field(
        ..., description="A user-friendly message describing the error"
    )
    code: Optional[str] = Field(
        None, description="An optional error code for API clients"
    )
    details: Optional[Any] = Field(
        None, description="Optional structured details about the error"
    )


class ApiSuccess(BaseModel, Generic[T]):
    status: str = Field(
        default="success", description="Indicates the response status is a success"
    )
    data: Optional[T] = Field(None, description="The payload of the response")


class ApiMessage(BaseModel):
    status: str = Field(
        default="success", description="Indicates the response status is a success"
    )
    message: str = Field(..., description="A status message")


class PaginatedResponse(BaseModel, Generic[T]):
    status: str = Field(
        default="success", description="Indicates the response status is a success"
    )
    data: List[T] = Field(..., description="List of items in the current page")
    page: int = Field(..., description="Current page number (1-indexed)")
    per_page: int = Field(..., description="Number of items per page")
    total: int = Field(..., description="Total number of items available")
    total_pages: int = Field(..., description="Total number of pages")
