"""Fixed Recruitment labels and display metadata."""

from __future__ import annotations

DEMO_CRITERIA = (
    "English fluency",
    "Lesson structure",
    "Board skills",
    "Student engagement",
    "Confidence & delivery",
)

PIPELINE_STAGE_COLOR_TOKENS = frozenset(
    {"neutral", "blue", "cyan", "violet", "green", "amber", "orange", "rose"}
)


__all__ = ["DEMO_CRITERIA", "PIPELINE_STAGE_COLOR_TOKENS"]
