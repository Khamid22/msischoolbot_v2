"""Typed request/response contracts for account security."""

from pydantic import BaseModel, Field


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)
    confirm_password: str = Field(min_length=1, max_length=256)


class PasswordChangeResult(BaseModel):
    changed: bool = True
    must_change_password: bool = False
    session_version: int = Field(ge=1)


__all__ = ["PasswordChangeRequest", "PasswordChangeResult"]
