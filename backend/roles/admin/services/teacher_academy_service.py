"""Compatibility import path for Teacher Academy domain service.

DB-1 moved the implementation to ``backend.domains.teacher_academy.service``.
Keep this module path alive so admin routes, HOD routes, and tests that import
the old service continue to receive the same module object.
"""

import sys

from backend.roles.admin import services as _services_package
from backend.domains.teacher_academy import service as _service

_compat_name = __name__
globals().update(_service.__dict__)
setattr(_services_package, "teacher_academy_service", _service)
sys.modules[_compat_name] = _service
