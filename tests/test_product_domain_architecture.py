"""Guards for the navigable product-domain modular monolith."""

from __future__ import annotations

from pathlib import Path


BACKEND_REQUIRED = {
    "people/ceo",
    "people/academic_director",
    "people/head_of_department",
    "people/hr_manager",
    "people/customer_support",
    "people/teacher",
    "people/student",
    "people/parent",
    "domains/identity",
    "domains/organization",
    "domains/student_records",
    "domains/parent_relationships",
    "domains/teacher_records",
    "domains/academics/curriculum",
    "domains/academics/groups",
    "domains/academics/timetable",
    "domains/academics/lessons",
    "domains/academics/attendance",
    "domains/academics/gradebook",
    "domains/academics/assessments",
    "domains/academics/calendar",
    "domains/academics/resources",
    "domains/recruitment",
    "domains/teacher_academy",
    "domains/support_cases",
    "domains/finance",
    "domains/communications",
    "domains/reporting",
    "jobs",
}

FRONTEND_REQUIRED = {
    "identity",
    "organization",
    "people/teachers",
    "academics/gradebook",
    "academics/curriculum",
    "academics/groups",
    "academics/timetable",
    "teacher-academy",
}

OBSOLETE_BACKEND_MODULES = {
    "accounts",
    "complaints",
    "learning_resources",
    "parent_access",
    "payments",
    "staff_records",
    "student_records",
}

CORE_REQUIRED = {"access", "api", "runtime", "web"}

INTERNAL_OPERATIONS_REQUIRED = {
    "pages",
    "academics",
    "people/students",
    "people/parents",
    "staffing",
    "resources",
    "finance",
    "support",
}

OBSOLETE_CORE_FILES = {
    "api_responses.py",
    "api_schemas.py",
    "assets.py",
    "config.py",
    "error_pages.py",
    "guards.py",
    "http.py",
    "observability.py",
    "passwords.py",
    "performance.py",
    "rate_limit.py",
    "rendering.py",
    "request_context.py",
    "session.py",
    "web_responses.py",
}

OBSOLETE_INTERNAL_OPERATION_FILES = {
    "academics_api.py",
    "academic_forms.py",
    "complaints_api.py",
    "learning_resources_api.py",
    "learning_resources_forms.py",
    "office_hours_api.py",
    "page.py",
    "page_cache.py",
    "parent_access_api.py",
    "payments_api.py",
    "schemas.py",
    "staff_records_forms.py",
    "student_records_api.py",
    "student_records_forms.py",
    "workspace.py",
}


def _python_sources(root: Path):
    return [path for path in root.rglob("*.py") if "__pycache__" not in path.parts]


def _web_sources(root: Path):
    return [path for path in root.rglob("*") if path.suffix in {".ts", ".tsx"}]


def test_implemented_product_domains_are_navigable_packages():
    root = Path("backend/modules")
    for relative in BACKEND_REQUIRED:
        domain = root / relative
        assert domain.is_dir(), f"Missing backend product domain: {relative}"
        assert (domain / "__init__.py").is_file(), f"Domain is not a package: {relative}"

    feature_root = Path("frontend/src/features")
    for relative in FRONTEND_REQUIRED:
        assert (feature_root / relative).is_dir(), f"Missing frontend product domain: {relative}"


def test_core_is_navigable_and_internal_operations_is_removed():
    core_root = Path("backend/core")
    for relative in CORE_REQUIRED:
        package = core_root / relative
        assert package.is_dir(), f"Missing Core responsibility package: {relative}"
        assert (package / "__init__.py").is_file()
    for file_name in OBSOLETE_CORE_FILES:
        assert not (core_root / file_name).exists(), f"Core flat file returned: {file_name}"
    assert not (core_root / "access/permissions.py").exists(), (
        "Keep API and workspace permission vocabularies in separate named files"
    )

    assert not Path("backend/internal_operations").exists()


def test_core_and_product_domains_do_not_depend_on_internal_operations():
    for root in (Path("backend/core"), Path("backend/modules")):
        for path in _python_sources(root):
            source = path.read_text(encoding="utf-8")
            assert "backend.internal_operations" not in source, (
                f"Outer system-admin adapter imported from {path}"
            )

    for path in _python_sources(Path("backend/core")):
        source = path.read_text(encoding="utf-8")
        assert "backend.modules" not in source, f"Product dependency leaked into Core: {path}"


def test_obsolete_ownership_packages_and_imports_are_absent():
    module_root = Path("backend/modules")
    for name in OBSOLETE_BACKEND_MODULES:
        assert not (module_root / name).exists()
    assert not Path("backend/integrations").exists()
    assert not Path("frontend/src/features/management").exists()
    assert not Path("frontend/src/features/accounts").exists()

    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [*_python_sources(Path("backend")), *_web_sources(Path("frontend/src"))]
    )
    for name in OBSOLETE_BACKEND_MODULES:
        assert f"backend.modules.{name}" not in source
    assert "backend.integrations" not in source
    assert "@/features/management" not in source


def test_recruitment_domain_does_not_restore_the_legacy_pipeline_or_lesson_practice():
    for path in (
        Path("backend/modules/domains/recruitment"),
        Path("frontend/src/features/recruitment"),
    ):
        assert path.exists()

    teacher_model = Path("frontend/src/features/people/teachers/model.ts").read_text()
    combined = teacher_model
    assert "Teacher Academy" in combined
    assert "Active Teachers" in combined
    assert "Hiring Pipeline" not in combined
    assert "Lesson Practice" not in combined
    assert "adminTeacherCandidates" not in combined
    assert not Path("frontend/src/features/teacher-academy/TrainingEvaluationModal.tsx").exists()


def test_runtime_postgresql_sql_is_repository_owned():
    for path in _python_sources(Path("backend/modules")):
        source = path.read_text(encoding="utf-8")
        if "conn.execute" not in source:
            continue
        assert "repository" in path.stem, f"Move SQL into an owning repository: {path}"


def test_removed_academic_catch_all_files_stay_removed():
    root = Path("backend/modules/domains/academics")
    for name in ("operations.py", "service.py", "repository.py"):
        assert not (root / name).exists()


def test_documented_size_exceptions_cover_existing_large_domain_files():
    module_map = Path("docs/ENGINEERING_MODULE_MAP.md").read_text(encoding="utf-8")
    roots_and_limits = (
        (Path("backend/modules"), "*.py", 800),
        (Path("backend/platform"), "*.py", 800),
        (Path("frontend/src/features"), "*.tsx", 600),
    )
    for root, pattern, limit in roots_and_limits:
        for path in root.rglob(pattern):
            if "__pycache__" in path.parts:
                continue
            line_count = len(path.read_text(encoding="utf-8").splitlines())
            if line_count <= limit:
                continue
            relative = path.relative_to(root).as_posix()
            assert relative in module_map, (
                f"{path} has {line_count} lines; split it or document a named exception"
            )
