def test_assessment_sections_collect_marking_criteria_scores_and_remarks():
    from backend.api.v1.teacher_academy.responses import assessment_sections_from_form

    form_data = {
        "teacher_guidance_compliance_score": "8",
        "teacher_guidance_compliance_remarks": "Followed the guide closely.",
        "timing_adherence_score": "7",
        "timing_adherence_remarks": "Starter ran long.",
        "resource_familiarity_score": "9",
        "resource_familiarity_remarks": "Used slides confidently.",
        "english_fluency_score": "8",
        "english_fluency_remarks": "Clear classroom language.",
        "confidence_delivery_score": "7",
        "confidence_delivery_remarks": "Needs stronger transitions.",
        "engagement_technique_score": "8",
        "engagement_technique_remarks": "Checked students often.",
    }

    sections = assessment_sections_from_form(form_data)

    criteria = sections["marking_criteria"]
    assert criteria["tgc"] == {"score": "8", "remarks": "Followed the guide closely."}
    assert criteria["ta"] == {"score": "7", "remarks": "Starter ran long."}
    assert criteria["rf"] == {"score": "9", "remarks": "Used slides confidently."}
    assert criteria["ef"] == {"score": "8", "remarks": "Clear classroom language."}
    assert criteria["con"] == {"score": "7", "remarks": "Needs stronger transitions."}
    assert criteria["se"] == {"score": "8", "remarks": "Checked students often."}
