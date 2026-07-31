"""Subject-curriculum contract errors."""


class CurriculumNotFoundError(LookupError):
    pass


class CurriculumPermissionError(PermissionError):
    pass


class CurriculumConflictError(RuntimeError):
    pass


class CurriculumValidationError(ValueError):
    pass


__all__ = [
    "CurriculumConflictError",
    "CurriculumNotFoundError",
    "CurriculumPermissionError",
    "CurriculumValidationError",
]
