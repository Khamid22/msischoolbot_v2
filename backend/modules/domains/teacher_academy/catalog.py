"""Fixed Teacher Academy scoring metadata."""

from __future__ import annotations

from types import MappingProxyType

RUBRIC_WEIGHTS = MappingProxyType(
    {
        "teacher_guidance_compliance_score": 0.25,
        "timing_adherence_score": 0.20,
        "resource_familiarity_score": 0.15,
        "english_fluency_score": 0.15,
        "confidence_delivery_score": 0.10,
        "engagement_technique_score": 0.15,
    }
)


__all__ = ["RUBRIC_WEIGHTS"]
