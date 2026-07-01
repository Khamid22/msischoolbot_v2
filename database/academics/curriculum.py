"""Official subject curriculum parsing and classification."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile

from database.academics import subjects


_MAIN_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_REL_NS = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
_REL_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


@dataclass(frozen=True)
class CurriculumSource:
    subject_name: str
    subject_short: str
    path: Path


@dataclass(frozen=True)
class CurriculumItem:
    subject_name: str
    subject_key: str
    subject_short: str
    source_file: str
    sheet_name: str
    row_number: int
    item_order: int
    lesson_number: str
    title: str
    item_type: str
    term_label: str
    week_label: str
    specification_points: str
    book_pages: str
    lesson_count: str
    duration_hours: str


DEFAULT_CURRICULUM_SOURCES = (
    CurriculumSource(
        "IGCSE Mathematics A",
        "Math",
        Path("/Users/apple/Downloads/IG Teaching Hubs MathsA SOW.xlsx"),
    ),
    CurriculumSource(
        "English as a Second Language",
        "Eng",
        Path("/Users/apple/Downloads/IG Teaching Hubs ESL SOW.xlsx"),
    ),
    CurriculumSource(
        "IGCSE Chemistry",
        "Chem",
        Path("/Users/apple/Downloads/IG Teaching Hubs Chemistry SOW.xlsx"),
    ),
    CurriculumSource(
        "IGCSE Biology",
        "Bio",
        Path("/Users/apple/Downloads/IG Teaching Hubs Biology SOW.xlsx"),
    ),
    CurriculumSource(
        "IGCSE Physics",
        "Phy",
        Path("/Users/apple/Downloads/IG Teaching Hubs Physics SOW.xlsx"),
    ),
)


def _normalize(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in str(cell_ref or "") if ch.isalpha())
    index = 0
    for ch in letters:
        index = index * 26 + ord(ch.upper()) - 64
    return index


def _read_shared_strings(zip_file: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(zip_file.read("xl/sharedStrings.xml"))
    except KeyError:
        return []

    values: list[str] = []
    for item in root.findall("a:si", _MAIN_NS):
        values.append("".join(text.text or "" for text in item.findall(".//a:t", _MAIN_NS)))
    return values


def _first_sheet_path(zip_file: ZipFile) -> tuple[str, str]:
    workbook = ET.fromstring(zip_file.read("xl/workbook.xml"))
    sheet = workbook.find("a:sheets/a:sheet", _MAIN_NS)
    if sheet is None:
        raise ValueError("Workbook does not contain a worksheet.")

    sheet_name = sheet.attrib.get("name", "Sheet1")
    rel_id = sheet.attrib.get(_REL_ID)
    rels = ET.fromstring(zip_file.read("xl/_rels/workbook.xml.rels"))
    target = "worksheets/sheet1.xml"
    for rel in rels.findall("rel:Relationship", _REL_NS):
        if rel.attrib.get("Id") == rel_id:
            target = rel.attrib.get("Target") or target
            break

    if target.startswith("/"):
        sheet_path = target.lstrip("/")
    else:
        sheet_path = f"xl/{target}"
    return sheet_name, sheet_path


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return _normalize("".join(text.text or "" for text in cell.findall(".//a:t", _MAIN_NS)))

    value = cell.find("a:v", _MAIN_NS)
    if value is None or value.text is None:
        return ""

    raw = value.text
    if cell_type == "s":
        try:
            return _normalize(shared_strings[int(raw)])
        except (IndexError, ValueError):
            return _normalize(raw)
    return _normalize(raw)


def _read_xlsx_rows(path: Path) -> tuple[str, list[tuple[int, dict[int, str]]]]:
    with ZipFile(path) as zip_file:
        shared_strings = _read_shared_strings(zip_file)
        sheet_name, sheet_path = _first_sheet_path(zip_file)
        root = ET.fromstring(zip_file.read(sheet_path))

    rows: list[tuple[int, dict[int, str]]] = []
    for row in root.findall(".//a:sheetData/a:row", _MAIN_NS):
        row_number = int(row.attrib.get("r", "0") or 0)
        values: dict[int, str] = {}
        for cell in row.findall("a:c", _MAIN_NS):
            column = _column_index(cell.attrib.get("r", ""))
            if column:
                values[column] = _cell_value(cell, shared_strings)
        if any(values.values()):
            rows.append((row_number, values))
    return sheet_name, rows


def _find_header(rows: list[tuple[int, dict[int, str]]]) -> tuple[int, dict[int, str]]:
    for row_number, values in rows:
        normalized = {column: _normalize(value).casefold() for column, value in values.items()}
        if "lesson number" in normalized.values() and "lesson name" in normalized.values():
            return row_number, normalized
    raise ValueError("Could not find lesson header row.")


def _column_for(header: dict[int, str], *labels: str) -> int | None:
    wanted = {label.casefold() for label in labels}
    for column, value in header.items():
        if value in wanted:
            return column
    return None


def classify_curriculum_item(title: str) -> str:
    normalized = _normalize(title).casefold()
    exam_patterns = (
        "half-term test",
        "end-of-term test",
        "end of term test",
        "end of year test",
        "mock exam",
        "mock unit test",
        "exam practice",
    )
    if any(pattern in normalized for pattern in exam_patterns):
        return "exam"
    return "lesson"


def parse_curriculum_source(source: CurriculumSource) -> list[CurriculumItem]:
    if not source.path.exists():
        raise FileNotFoundError(source.path)

    sheet_name, rows = _read_xlsx_rows(source.path)
    header_row, header = _find_header(rows)
    term_col = _column_for(header, "year and term")
    week_col = _column_for(header, "week")
    number_col = _column_for(header, "lesson number")
    title_col = _column_for(header, "lesson name")
    spec_col = _column_for(header, "specification point(s)", "assessment objectives")
    pages_col = _column_for(header, "student book pages", "student book page reference")
    lesson_count_col = _column_for(header, "no. of lesson")
    duration_col = _column_for(header, "no. of hours (0.66 = 40 mins)")

    if number_col is None or title_col is None:
        raise ValueError("Lesson number/title columns are required.")

    subject_name = subjects.canonical_subject_name(source.subject_name)
    subject_key = subjects.subject_key(subject_name)
    subject_short = source.subject_short or subjects.subject_short_name(subject_name)

    items: list[CurriculumItem] = []
    for row_number, values in rows:
        if row_number <= header_row:
            continue
        lesson_number = _normalize(values.get(number_col, ""))
        title = _normalize(values.get(title_col, ""))
        if not lesson_number and not title:
            continue
        match = re.search(r"\bLesson\s+(\d+)\b", lesson_number, flags=re.IGNORECASE)
        if not match:
            continue

        items.append(
            CurriculumItem(
                subject_name=subject_name,
                subject_key=subject_key,
                subject_short=subject_short,
                source_file=source.path.name,
                sheet_name=sheet_name,
                row_number=row_number,
                item_order=int(match.group(1)),
                lesson_number=f"Lesson {int(match.group(1))}",
                title=title,
                item_type=classify_curriculum_item(title),
                term_label=_normalize(values.get(term_col, "")) if term_col else "",
                week_label=_normalize(values.get(week_col, "")) if week_col else "",
                specification_points=_normalize(values.get(spec_col, "")) if spec_col else "",
                book_pages=_normalize(values.get(pages_col, "")) if pages_col else "",
                lesson_count=_normalize(values.get(lesson_count_col, "")) if lesson_count_col else "",
                duration_hours=_normalize(values.get(duration_col, "")) if duration_col else "",
            )
        )
    return sorted(items, key=lambda item: item.item_order)


def load_default_curricula() -> dict[str, list[CurriculumItem]]:
    curricula: dict[str, list[CurriculumItem]] = {}
    for source in DEFAULT_CURRICULUM_SOURCES:
        items = parse_curriculum_source(source)
        if items:
            curricula[items[0].subject_key] = items
    return curricula


__all__ = [
    "CurriculumItem",
    "CurriculumSource",
    "DEFAULT_CURRICULUM_SOURCES",
    "classify_curriculum_item",
    "load_default_curricula",
    "parse_curriculum_source",
]
