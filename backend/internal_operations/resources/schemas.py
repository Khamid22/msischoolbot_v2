"""Response contracts for system-admin learning-resource routes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AdminResourceList(BaseModel):
    resources: list[dict[str, Any]]


class AdminResourceUploadProgress(BaseModel):
    events: list[dict[str, Any]]
    latest_seq: int
    done: bool
