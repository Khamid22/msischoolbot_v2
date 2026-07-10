"""Text normalization helpers shared across academic rules."""


def normalize_text(value):
    """Casefold and collapse internal whitespace."""
    return " ".join(str(value or "").strip().casefold().split())


__all__ = ["normalize_text"]
