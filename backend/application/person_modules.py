"""Explicit registry for person-owned orchestration modules."""

from backend.application.module_spec import PersonModuleRegistry
from backend.modules.people.academic_director.module import PERSON_MODULE as ACADEMIC_DIRECTOR
from backend.modules.people.ceo.module import PERSON_MODULE as CEO
from backend.modules.people.customer_support.module import PERSON_MODULE as CUSTOMER_SUPPORT
from backend.modules.people.head_of_department.module import PERSON_MODULE as HEAD_OF_DEPARTMENT
from backend.modules.people.hr_manager.module import PERSON_MODULE as HR_MANAGER
from backend.modules.people.parent.module import PERSON_MODULE as PARENT
from backend.modules.people.student.module import PERSON_MODULE as STUDENT
from backend.modules.people.teacher.module import PERSON_MODULE as TEACHER

PERSON_MODULES = PersonModuleRegistry(
    (
        CEO,
        ACADEMIC_DIRECTOR,
        HEAD_OF_DEPARTMENT,
        HR_MANAGER,
        CUSTOMER_SUPPORT,
        TEACHER,
        STUDENT,
        PARENT,
    )
)

__all__ = ["PERSON_MODULES"]
