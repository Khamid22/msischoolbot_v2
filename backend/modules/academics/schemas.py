"""Academic Director API v1 schemas."""

from __future__ import annotations

from pydantic import BaseModel


class CreateHeadOfDepartmentForm(BaseModel):
    hod_display_name: str = ""
    hod_subject_id: str = ""


class HeadOfDepartmentCredentials(BaseModel):
    role: str = "head_of_department"
    login: str = ""
    temporary_password: str = ""
    display_name: str = ""
    subject_name: str = ""


class HeadOfDepartmentAccount(BaseModel):
    login: str = ""
    display_name: str = ""
    role: str = "head_of_department"
    status: str = "active"
    subject_name: str = ""


class HeadOfDepartmentCreated(BaseModel):
    message: str
    credentials: HeadOfDepartmentCredentials
    headOfDepartment: HeadOfDepartmentAccount


class HeadOfDepartmentPasswordReset(BaseModel):
    message: str
    login: str
    temporary_password: str
    display_name: str = ""
    must_change_password: bool = True
    updated_at: str = ""
