
from __future__ import annotations

from app.core.model_loader import (
    get_model_bundle,
)

from app.services.inference import (
    run_inference,
)


# ============================================================
# Helpers
# ============================================================

def _safe_filename(
    filename,
) -> str:

    if filename:
        return str(filename)

    return "Filename unavailable"


def _build_positive_factors(
    inference_result: dict,
) -> list[str]:

    factors = []

    semantic_score = float(
        inference_result.get(
            "semantic_score",
            0.0,
        )
    )

    skill_score = float(
        inference_result.get(
            "skill_score",
            0.0,
        )
    )

    experience_score = float(
        inference_result.get(
            "experience_score",
            0.0,
        )
    )

    matched_skill_count = int(
        inference_result.get(
            "matched_skill_count",
            0,
        )
    )

    required_experience_years = (
        inference_result.get(
            "required_experience_years"
        )
    )

    candidate_experience_years = (
        inference_result.get(
            "candidate_experience_years"
        )
    )

    if semantic_score >= 0.70:
        factors.append(
            "Strong semantic similarity between the resume and job description"
        )
    elif semantic_score >= 0.50:
        factors.append(
            "Moderate semantic similarity between the resume and job description"
        )

    if skill_score >= 1.0:
        factors.append(
            "All required skills were demonstrated"
        )
    elif skill_score > 0:
        factors.append(
            f"{matched_skill_count} required skill(s) were demonstrated"
        )

    if (
        candidate_experience_years is not None
        and required_experience_years is not None
        and candidate_experience_years >= required_experience_years
    ):
        factors.append(
            "Candidate experience meets the stated requirement"
        )

    return factors


def _build_review_flags(
    inference_result: dict,
) -> list[str]:

    flags = []

    missing_skills = inference_result.get(
        "missing_skills",
        [],
    )

    if missing_skills:
        flags.append(
            "Missing required skills: "
            + ", ".join(missing_skills)
        )

    pre_screen = inference_result.get(
        "pre_screen",
        {}
    )

    for reason in pre_screen.get(
        "review_reasons",
        [],
    ):

        if reason not in flags:
            flags.append(reason)

    return flags


def _build_similar_resumes(
    inference_result: dict,
) -> list[dict]:

    results = []

    for item in inference_result.get(
        "similar_resumes",
        [],
    ):

        results.append({
            "candidate_id": item.get(
                "candidate_id"
            ),
            "filename": _safe_filename(
                item.get("filename")
            ),
            "similarity": round(
                float(
                    item.get(
                        "similarity",
                        0.0,
                    )
                ),
                4,
            ),
        })

    return results


def _build_feature_importance() -> list[dict]:

    bundle = get_model_bundle()

    model = bundle[
        "random_forest_model"
    ]

    feature_columns = list(
        bundle[
            "feature_columns"
        ]
    )

    importances = getattr(
        model,
        "feature_importances_",
        None,
    )

    if importances is None:
        return []

    pairs = sorted(
        zip(
            feature_columns,
            importances,
        ),
        key=lambda item: item[1],
        reverse=True,
    )

    return [
        {
            "feature": feature,
            "importance": round(
                float(value),
                6,
            ),
        }
        for feature, value in pairs
    ]


# ============================================================
# Main explanation builder
# ============================================================

def build_explanation(
    inference_result: dict,
) -> dict:

    if not isinstance(
        inference_result,
        dict,
    ):
        raise TypeError(
            "inference_result must be a dictionary"
        )

    pre_screen = inference_result.get(
        "pre_screen",
        {},
    )

    return {
        "match_score": round(
            float(
                inference_result.get(
                    "match_score",
                    0.0,
                )
            ),
            4,
        ),

        "match_score_percent": round(
            float(
                inference_result.get(
                    "match_score_percent",
                    0.0,
                )
            ),
            2,
        ),

        "pre_screen": {
            "status": pre_screen.get(
                "status",
                "NEEDS_REVIEW",
            ),
            "ready": bool(
                pre_screen.get(
                    "ready",
                    False,
                )
            ),
        },

        "positive_factors": (
            _build_positive_factors(
                inference_result
            )
        ),

        "review_flags": (
            _build_review_flags(
                inference_result
            )
        ),

        "skills": {
            "matched": inference_result.get(
                "matched_skills",
                [],
            ),
            "missing": inference_result.get(
                "missing_skills",
                [],
            ),
            "matched_count": int(
                inference_result.get(
                    "matched_skill_count",
                    0,
                )
            ),
            "missing_count": int(
                inference_result.get(
                    "missing_skill_count",
                    0,
                )
            ),
        },

        "experience": {
            "candidate_years": (
                inference_result.get(
                    "candidate_experience_years"
                )
            ),
            "candidate_display": (
                inference_result.get(
                    "candidate_experience_display"
                )
            ),
            "required_years": (
                inference_result.get(
                    "required_experience_years"
                )
            ),
            "required_display": (
                inference_result.get(
                    "required_experience_display"
                )
            ),
            "experience_score": round(
                float(
                    inference_result.get(
                        "experience_score",
                        0.0,
                    )
                ),
                4,
            ),
        },

        "model_scores": {
            "semantic_score": round(
                float(
                    inference_result.get(
                        "semantic_score",
                        0.0,
                    )
                ),
                4,
            ),
            "skill_score": round(
                float(
                    inference_result.get(
                        "skill_score",
                        0.0,
                    )
                ),
                4,
            ),
            "experience_score": round(
                float(
                    inference_result.get(
                        "experience_score",
                        0.0,
                    )
                ),
                4,
            ),
        },

        "cluster": int(
            inference_result.get(
                "cluster",
                -1,
            )
        ),

        "similar_resumes": (
            _build_similar_resumes(
                inference_result
            )
        ),

        "model_features": (
            inference_result.get(
                "model_features",
                {},
            )
        ),

        "feature_importance": (
            _build_feature_importance()
        ),

        "decision_note": (
            "The ML match score is a screening signal "
            "based on the available resume and job data. "
            "It is not a hiring probability or hiring decision."
        ),
    }


# ============================================================
# Complete screening + explanation
# ============================================================

def screen_with_explanation(
    resume_file_content: bytes,
    resume_filename: str,
    job_description: str,
    job_title: str = "Untitled Job",
    similar_top_k: int = 5,
) -> dict:

    inference_result = run_inference(
        resume_file_content=resume_file_content,
        resume_filename=resume_filename,
        job_description=job_description,
        job_title=job_title,
        similar_top_k=similar_top_k,
    )

    explanation = build_explanation(
        inference_result
    )

    return {
        **explanation,

        "candidate": {
            "filename": resume_filename,
            "skills": inference_result[
                "resume"
            ].get(
                "skills",
                [],
            ),
            "education": inference_result[
                "resume"
            ].get(
                "education",
                [],
            ),
        },

        "job": {
            "title": inference_result[
                "job"
            ].get(
                "job_title",
                job_title,
            ),
            "required_skills": inference_result[
                "job"
            ].get(
                "required_skills",
                [],
            ),
            "preferred_skills": inference_result[
                "job"
            ].get(
                "preferred_skills",
                [],
            ),
            "required_experience": inference_result[
                "job"
            ].get(
                "required_experience"
            ),
            "required_education": inference_result[
                "job"
            ].get(
                "required_education",
                [],
            ),
        },
    }
