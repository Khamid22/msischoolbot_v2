from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from sheets_data import SheetsDataError, _get_sheets_service, get_school_dataset


def load_env_file(path: Path) -> None:
    if not path.exists() or not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue

        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]

        os.environ[key] = value


def ensure_env_loaded(base_dir: Path) -> None:
    # Load local and parent env files for convenience during terminal testing.
    load_env_file(base_dir / ".env")
    load_env_file(base_dir.parent / ".env")


def resolve_credentials_path(base_dir: Path, explicit_path: str | None) -> Path | None:
    if explicit_path:
        path = Path(explicit_path).expanduser().resolve()
        return path if path.exists() else None

    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        path = Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]).expanduser().resolve()
        return path if path.exists() else None

    candidates = [
        base_dir / "credentials.json",
        base_dir.parent / "credentials.json",
        Path.cwd() / "credentials.json",
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()

    return None


def list_raw_sheet_titles(spreadsheet_id: str) -> list[str]:
    service = _get_sheets_service()
    metadata = (
        service.spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            fields="properties(title),sheets(properties(title))",
        )
        .execute()
    )

    spreadsheet_title = metadata.get("properties", {}).get("title", "(unknown)")
    titles = [
        sheet.get("properties", {}).get("title", "")
        for sheet in metadata.get("sheets", [])
        if sheet.get("properties", {}).get("title")
    ]

    print(f"Spreadsheet: {spreadsheet_title}")
    print(f"Tabs found: {len(titles)}")
    for title in titles:
        print(f"  - {title}")
    print()
    return titles


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Test Google Sheets connectivity and parsed dataset for MSI web app.",
    )
    parser.add_argument(
        "--spreadsheet-id",
        help="Google Sheets spreadsheet ID (falls back to GOOGLE_SHEETS_SPREADSHEET_ID env).",
    )
    parser.add_argument(
        "--credentials",
        help="Path to service account JSON (falls back to credentials.json auto-detection).",
    )
    parser.add_argument(
        "--show-students",
        type=int,
        default=10,
        help="How many parsed students to print (default: 10).",
    )
    parser.add_argument(
        "--no-list-tabs",
        action="store_true",
        help="Skip raw sheet tabs listing step.",
    )
    return parser


def print_dataset_summary(dataset: dict[str, Any], show_students: int) -> None:
    students = dataset.get("students", [])
    groups = dataset.get("groups", [])
    subjects = dataset.get("subjects", [])

    print("Parsed dataset summary")
    print(f"  Subjects: {len(subjects)} -> {', '.join(subjects) if subjects else '(none)'}")
    print(f"  Groups: {len(groups)}")
    for group in groups:
        print(f"    - {group}")

    print(f"  Students parsed: {len(students)}")
    preview_count = min(max(show_students, 0), len(students))
    if preview_count > 0:
        print(f"  First {preview_count} students:")
        for student in students[:preview_count]:
            print(
                "    - "
                f"id={student.get('id')} | "
                f"name={student.get('fullName')} | "
                f"group={student.get('group')} | "
                f"subject={student.get('subject')}"
            )

    print()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    ensure_env_loaded(base_dir)

    if args.spreadsheet_id:
        os.environ["GOOGLE_SHEETS_SPREADSHEET_ID"] = args.spreadsheet_id

    spreadsheet_id = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID", "").strip()
    if not spreadsheet_id:
        print("ERROR: GOOGLE_SHEETS_SPREADSHEET_ID is missing.")
        print("Set it in env/.env or pass --spreadsheet-id.")
        return 1

    if not os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        credentials_path = resolve_credentials_path(base_dir, args.credentials)
        if not credentials_path:
            print("ERROR: Service account credentials not found.")
            print("Provide --credentials path or set GOOGLE_APPLICATION_CREDENTIALS.")
            return 1
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)

    print("Google Sheets test started")
    print(f"Spreadsheet ID: {spreadsheet_id}")
    print(
        "Credentials source: "
        + (
            "GOOGLE_SERVICE_ACCOUNT_JSON"
            if os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
            else os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "(not set)")
        )
    )
    print()

    try:
        if not args.no_list_tabs:
            list_raw_sheet_titles(spreadsheet_id)

        dataset = get_school_dataset(force_refresh=True)
        print_dataset_summary(dataset, args.show_students)

        if dataset.get("students"):
            sample_student = dataset["students"][0]
            print("Sample dashboard URL for testing in browser:")
            print(f"  http://127.0.0.1:5000/dashboard/{sample_student['id']}")
        else:
            print("No students parsed from recognized group tabs.")
            print("Check group tab names like MMG1, MAFTG2, ENGMG1, etc.")

        return 0
    except SheetsDataError as exc:
        print(f"SheetsDataError: {exc}")
        return 2
    except Exception as exc:
        print(f"Unexpected error: {exc}")
        return 3


if __name__ == "__main__":
    sys.exit(main())
