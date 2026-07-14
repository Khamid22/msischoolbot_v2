"""Organization academic operations."""


from backend.modules.organization.service import create_class, create_school, create_subject

def create_subject_from_payload(payload):
    school_code = str(payload.get("school_code", "") or "").strip()
    subject_name = str(payload.get("subject_name", "") or "").strip()
    subject_code = str(payload.get("subject_code", "") or "").strip()
    if not school_code or not subject_name:
        raise ValueError("School and subject name are required.")
    create_subject(school_code, subject_name, subject_code)
    return {"school_code": school_code}


def create_class_from_payload(payload):
    school_code = str(payload.get("school_code", "") or "").strip()
    class_name = str(payload.get("class_name", "") or "").strip()
    class_code = str(payload.get("class_code", "") or "").strip()
    if not school_code or not class_name:
        raise ValueError("Client school and class name are required.")
    return create_class(school_code, class_name, class_code)


def create_school_from_payload(payload):
    name = str(payload.get("school_name", "") or "").strip()
    code = str(payload.get("school_code", "") or "").strip()
    if not name:
        raise ValueError("School name is required.")
    create_school(name, code)
    return {"name": name}
