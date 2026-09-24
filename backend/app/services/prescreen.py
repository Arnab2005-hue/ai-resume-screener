
from __future__ import annotations

import re


# ============================================================
# Text normalization
# ============================================================

def _normalize_text(
    value,
) -> str:

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip().casefold()


def _skill_key(
    skill: str,
) -> str:

    return _normalize_text(
        skill
    )


# ============================================================
# Required-skill check
# ============================================================

def check_required_skills(
    candidate_skills,
    required_skills,
) -> dict:

    candidate_keys = {
        _skill_key(skill)
        for skill in (candidate_skills or [])
        if _skill_key(skill)
    }

    required_keys = {
        _skill_key(skill)
        for skill in (required_skills or [])
        if _skill_key(skill)
    }

    matched = []
    missing = []

    for skill in (
        required_skills or []
    ):

        key = _skill_key(skill)

        if key in candidate_keys:
            matched.append(skill)
        else:
            missing.append(skill)

    return {
        "required_count": len(
            required_skills or []
        ),
        "matched_count": len(matched),
        "missing_count": len(missing),
        "matched_skills": matched,
        "missing_skills": missing,
        "ready": len(missing) == 0,
    }


# ============================================================
# Experience check
# ============================================================

def check_experience(
    candidate_experience_years,
    candidate_experience_missing,
    required_experience_years,
) -> dict:

    if required_experience_years is None:
        return {
            "required_experience_years": None,
            "candidate_experience_years": (
                candidate_experience_years
            ),
            "candidate_experience_missing": (
                bool(candidate_experience_missing)
            ),
            "status": "NOT_SPECIFIED",
            "ready": True,
        }

    if candidate_experience_missing:
        return {
            "required_experience_years": (
                required_experience_years
            ),
            "candidate_experience_years": None,
            "candidate_experience_missing": True,
            "status": "NOT_DEMONSTRATED",
            "ready": False,
        }

    if candidate_experience_years is None:
        return {
            "required_experience_years": (
                required_experience_years
            ),
            "candidate_experience_years": None,
            "candidate_experience_missing": True,
            "status": "NOT_DEMONSTRATED",
            "ready": False,
        }

    candidate_years = float(
        candidate_experience_years
    )

    required_years = float(
        required_experience_years
    )

    if candidate_years >= required_years:
        status = "MEETS_REQUIREMENT"
        ready = True
    else:
        status = "BELOW_REQUIREMENT"
        ready = False

    return {
        "required_experience_years": (
            required_years
        ),
        "candidate_experience_years": (
            candidate_years
        ),
        "candidate_experience_missing": False,
        "status": status,
        "ready": ready,
    }


# ============================================================
# Education normalization
# ============================================================

def _education_category(
    education: str,
) -> str:

    value = _normalize_text(
        education
    )

    if not value:
        return ""

    if (
        "bca" in value
        or "b.tech" in value
        or "btech" in value
        or "b.e" in value
        or "be " in value
        or "bachelor" in value
    ):
        return "bachelor"

    if (
        "mca" in value
        or "m.tech" in value
        or "mtech" in value
        or "m.e" in value
        or "me " in value
        or "mba" in value
        or "master" in value
    ):
        return "master"

    if "phd" in value:
        return "phd"

    return value


def _required_education_categories(
    required_education,
) -> set[str]:

    return {
        _education_category(item)
        for item in (
            required_education or []
        )
        if _education_category(item)
    }


def _candidate_education_categories(
    candidate_education,
) -> set[str]:

    return {
        _education_category(item)
        for item in (
            candidate_education or []
        )
        if _education_category(item)
    }


# ============================================================
# Education check
# ============================================================

def check_education(
    candidate_education,
    required_education,
) -> dict:

    required_categories = (
        _required_education_categories(
            required_education
        )
    )

    candidate_categories = (
        _candidate_education_categories(
            candidate_education
        )
    )

    if not required_categories:
        return {
            "required_education": (
                required_education or []
            ),
            "candidate_education": (
                candidate_education or []
            ),
            "missing_education": [],
            "status": "NOT_SPECIFIED",
            "ready": True,
        }

    matched_categories = (
        required_categories
        & candidate_categories
    )

    missing_categories = (
        required_categories
        - candidate_categories
    )

    return {
        "required_education": (
            required_education or []
        ),
        "candidate_education": (
            candidate_education or []
        ),
        "matched_categories": sorted(
            matched_categories
        ),
        "missing_education": sorted(
            missing_categories
        ),
        "status": (
            "MEETS_REQUIREMENT"
            if not missing_categories
            else "NOT_DEMONSTRATED"
        ),
        "ready": not bool(
            missing_categories
        ),
    }


# ============================================================
# Main pre-screen
# ============================================================

def run_pre_screen(
    resume: dict,
    job: dict,
) -> dict:

    if not isinstance(
        resume,
        dict,
    ):
        raise TypeError(
            "resume must be a dictionary"
        )

    if not isinstance(
        job,
        dict,
    ):
        raise TypeError(
            "job must be a dictionary"
        )

    review_reasons = []
    positive_checks = []

    # --------------------------------------------------------
    # Basic readability
    # --------------------------------------------------------

    resume_text = resume.get(
        "resume_text",
        "",
    )

    readable = bool(
        isinstance(
            resume_text,
            str,
        )
        and resume_text.strip()
    )

    if not readable:
        review_reasons.append(
            "Resume text could not be read"
        )
    else:
        positive_checks.append(
            "Resume text is readable"
        )

    # --------------------------------------------------------
    # Required skills
    # --------------------------------------------------------

    skill_result = check_required_skills(
        candidate_skills=resume.get(
            "skills",
            [],
        ),
        required_skills=job.get(
            "required_skills",
            [],
        ),
    )

    if skill_result["missing_count"] > 0:

        review_reasons.append(
            "Missing required skills: "
            + ", ".join(
                skill_result[
                    "missing_skills"
                ]
            )
        )

    else:

        if skill_result["required_count"] > 0:
            positive_checks.append(
                "All required skills demonstrated"
            )
        else:
            positive_checks.append(
                "No required skills specified"
            )

    # --------------------------------------------------------
    # Experience
    # --------------------------------------------------------

    experience_result = check_experience(
        candidate_experience_years=resume.get(
            "experience_years"
        ),
        candidate_experience_missing=resume.get(
            "experience_missing",
            True,
        ),
        required_experience_years=job.get(
            "required_experience_years"
        ),
    )

    if experience_result["status"] == (
        "NOT_DEMONSTRATED"
    ):

        review_reasons.append(
            "Required experience is not demonstrated"
        )

    elif experience_result["status"] == (
        "BELOW_REQUIREMENT"
    ):

        review_reasons.append(
            "Candidate experience is below "
            "the stated requirement"
        )

    elif experience_result["status"] == (
        "MEETS_REQUIREMENT"
    ):

        positive_checks.append(
            "Required experience demonstrated"
        )

    else:

        positive_checks.append(
            "Experience requirement not specified"
        )

    # --------------------------------------------------------
    # Education
    # --------------------------------------------------------

    education_result = check_education(
        candidate_education=resume.get(
            "education",
            [],
        ),
        required_education=job.get(
            "required_education",
            [],
        ),
    )

    if not education_result["ready"]:

        missing_education = education_result.get(
            "missing_education",
            [],
        )

        if missing_education:
            review_reasons.append(
                "Required education not demonstrated"
            )
        else:
            review_reasons.append(
                "Required education could not be verified"
            )

    else:

        if education_result["status"] == (
            "MEETS_REQUIREMENT"
        ):
            positive_checks.append(
                "Required education demonstrated"
            )
        else:
            positive_checks.append(
                "Education requirement not specified"
            )

    # --------------------------------------------------------
    # Final status
    # --------------------------------------------------------

    status = (
        "READY"
        if not review_reasons
        else "NEEDS_REVIEW"
    )

    return {
        "status": status,
        "ready": status == "READY",

        "review_reasons": review_reasons,

        "positive_checks": positive_checks,

        "required_skill_check": (
            skill_result
        ),

        "experience_check": (
            experience_result
        ),

        "education_check": (
            education_result
        ),
    }


# ============================================================
# File-based convenience function
# ============================================================

def pre_screen_resume(
    file_content: bytes,
    filename: str,
    job_description: str,
    job_title: str = "Untitled Job",
) -> dict:

    from app.services.resume_job_processing import (
        parse_resume,
        parse_job_description,
    )

    resume = parse_resume(
        file_content=file_content,
        filename=filename,
    )

    job = parse_job_description(
        job_description=job_description,
        job_title=job_title,
    )

    result = run_pre_screen(
        resume=resume,
        job=job,
    )

    return {
        **result,
        "resume": resume,
        "job": job,
    }
