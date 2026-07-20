"""Recruitment domain errors shared by focused HR capabilities."""

from __future__ import annotations

from typing import Any


class RecruitmentError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        code: str = "",
        details: Any = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.details = details


__all__ = ["RecruitmentError"]
