"""Durable, idempotent PowerPoint-to-slide conversion."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from backend.core.unit_of_work import UnitOfWorkFactory
from backend.modules.domains.academics.subject_curriculum import presentation_repository
from backend.platform.storage.r2 import (
    download_private_curriculum_object,
    upload_private_curriculum_rendition,
)

MAX_PRESENTATION_SLIDES = 200
CONVERSION_TIMEOUT_SECONDS = 180


def _binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"{name} is unavailable in the curriculum worker.")
    return path


def _run(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=CONVERSION_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        summary = (completed.stderr or completed.stdout or "Conversion failed.").strip()
        raise RuntimeError(summary[:500])
    return completed.stdout


def _page_count(pdf_path: Path) -> int:
    output = _run([_binary("pdfinfo"), str(pdf_path)])
    match = re.search(r"^Pages:\s+(\d+)\s*$", output, flags=re.MULTILINE)
    if not match:
        raise RuntimeError("The converted presentation has no readable slide count.")
    count = int(match.group(1))
    if count <= 0:
        raise RuntimeError("The converted presentation contains no slides.")
    if count > MAX_PRESENTATION_SLIDES:
        raise RuntimeError(
            f"Presentations may contain at most {MAX_PRESENTATION_SLIDES} slides."
        )
    return count


def _slide_number(path: Path) -> int:
    match = re.search(r"-(\d+)\.png$", path.name)
    return int(match.group(1)) if match else 0


def _mark_failed(
    factory: UnitOfWorkFactory,
    *,
    asset_id: int,
    error: Exception,
) -> None:
    with factory.transaction() as unit_of_work:
        presentation_repository.mark_conversion_failed(
            unit_of_work.conn,
            asset_id,
            str(error) or "Presentation conversion failed.",
        )
        unit_of_work.commit()


def convert_presentation_asset(
    asset_id: int,
    *,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
) -> None:
    factory = unit_of_work_factory or UnitOfWorkFactory()
    with factory.transaction() as unit_of_work:
        current = presentation_repository.get_asset_row(
            unit_of_work.conn,
            asset_id,
            for_update=True,
        )
        if not current:
            return
        if str(current["conversion_status"]) == "ready":
            unit_of_work.commit()
            return
        processing = presentation_repository.mark_conversion_processing(
            unit_of_work.conn,
            asset_id,
        )
        if not processing:
            unit_of_work.commit()
            return
        object_key = str(processing["object_key"])
        original_name = str(processing["original_file_name"])
        unit_of_work.commit()

    try:
        with tempfile.TemporaryDirectory(prefix="msi-curriculum-slides-") as directory:
            workdir = Path(directory)
            suffix = Path(original_name).suffix.casefold() or ".pptx"
            source_path = workdir / f"presentation{suffix}"
            if not download_private_curriculum_object(object_key, source_path):
                raise RuntimeError("Unable to download the private presentation.")
            _run(
                [
                    _binary("soffice"),
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(workdir),
                    str(source_path),
                ]
            )
            pdf_path = workdir / "presentation.pdf"
            if not pdf_path.exists():
                raise RuntimeError("PowerPoint conversion did not produce a PDF.")
            expected_count = _page_count(pdf_path)
            slide_prefix = workdir / "slide"
            _run(
                [
                    _binary("pdftoppm"),
                    "-png",
                    "-r",
                    "120",
                    str(pdf_path),
                    str(slide_prefix),
                ]
            )
            slide_paths = sorted(workdir.glob("slide-*.png"), key=_slide_number)
            if len(slide_paths) != expected_count:
                raise RuntimeError("Converted slide output is incomplete.")
            uploaded: list[dict[str, object]] = []
            for slide_number, slide_path in enumerate(slide_paths, start=1):
                metadata, error = upload_private_curriculum_rendition(
                    slide_path,
                    asset_id=asset_id,
                    slide_number=slide_number,
                )
                if error:
                    raise RuntimeError(error)
                uploaded.append(
                    {
                        **metadata,
                        "slide_number": slide_number,
                    }
                )
        with factory.transaction() as unit_of_work:
            current = presentation_repository.get_asset_row(
                unit_of_work.conn,
                asset_id,
                for_update=True,
            )
            if not current or str(current["conversion_status"]) == "ready":
                unit_of_work.commit()
                return
            for slide in uploaded:
                presentation_repository.insert_rendition(
                    unit_of_work.conn,
                    asset_id=asset_id,
                    slide_number=int(str(slide["slide_number"])),
                    object_key=str(slide["object_key"]),
                    mime_type=str(slide["mime_type"]),
                    size_bytes=int(str(slide["size_bytes"])),
                )
            presentation_repository.mark_conversion_ready(unit_of_work.conn, asset_id)
            unit_of_work.commit()
    except Exception as exc:
        _mark_failed(factory, asset_id=asset_id, error=exc)
        raise


__all__ = [
    "CONVERSION_TIMEOUT_SECONDS",
    "MAX_PRESENTATION_SLIDES",
    "convert_presentation_asset",
]
