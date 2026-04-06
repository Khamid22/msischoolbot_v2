import re
from pathlib import Path


_IMPORT_RE = re.compile(
    r'^\s*@import\s+url\((?P<quote>["\']?)(?P<path>[^)"\']+)(?P=quote)\)\s*;\s*$',
    re.MULTILINE,
)


def _resolve_css_sources(entry_path):
    resolved = []
    seen = set()

    def visit(path):
        path = Path(path).resolve()
        if path in seen:
            return
        seen.add(path)

        try:
            source_text = path.read_text(encoding="utf-8")
        except OSError:
            return

        for match in _IMPORT_RE.finditer(source_text):
            import_target = match.group("path").strip()
            if not import_target:
                continue
            if import_target.startswith(("http://", "https://", "//")):
                continue
            visit(path.parent / import_target)

        resolved.append(path)

    visit(entry_path)
    return resolved


def build_css_bundle(entry_path, output_path):
    entry_file = Path(entry_path).resolve()
    output_file = Path(output_path).resolve()
    source_files = _resolve_css_sources(entry_file)

    sections = [
        "/* Generated file. Do not edit directly. */",
        f"/* Source manifest: {entry_file.name} */",
        "",
    ]
    for source_file in source_files:
        relative_label = source_file.relative_to(output_file.parent)
        source_text = source_file.read_text(encoding="utf-8")
        source_text = _IMPORT_RE.sub("", source_text).strip()
        if not source_text:
            continue
        sections.append(f"/* Source: {relative_label.as_posix()} */")
        sections.append(source_text)
        sections.append("")

    bundled_text = "\n".join(sections).rstrip() + "\n"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(bundled_text, encoding="utf-8")
    return source_files


def ensure_css_bundle(entry_path, output_path):
    entry_file = Path(entry_path).resolve()
    output_file = Path(output_path).resolve()
    source_files = _resolve_css_sources(entry_file)

    if not source_files:
        raise FileNotFoundError(f"No CSS sources resolved from {entry_file}")

    if not output_file.exists():
        build_css_bundle(entry_file, output_file)
        return True

    try:
        output_mtime = output_file.stat().st_mtime
    except OSError:
        build_css_bundle(entry_file, output_file)
        return True

    latest_source_mtime = max(source_file.stat().st_mtime for source_file in source_files)
    if latest_source_mtime > output_mtime:
        build_css_bundle(entry_file, output_file)
        return True

    return False
