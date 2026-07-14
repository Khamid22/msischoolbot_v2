"""Public persistence contract used by Teacher Academy transactions."""

from backend.modules.people.teachers import repository


get_teacher_by_full_name_row = repository.get_teacher_by_full_name_row
insert_teacher_profile_row = repository.insert_teacher_profile_row
upsert_teacher_subject = repository.upsert_teacher_subject
get_teacher_auth_row_by_id = repository.get_teacher_auth_row_by_id
get_next_teacher_code = repository.get_next_teacher_code
insert_teacher_auth = repository.insert_teacher_auth
activate_teacher_profile = repository.activate_teacher_profile
set_teacher_group_assignment = repository.set_teacher_group_assignment


__all__ = [
    "activate_teacher_profile",
    "get_next_teacher_code",
    "get_teacher_auth_row_by_id",
    "get_teacher_by_full_name_row",
    "insert_teacher_auth",
    "insert_teacher_profile_row",
    "set_teacher_group_assignment",
    "upsert_teacher_subject",
]
