
import hashlib
import re

from sqlalchemy import select

from app.core.database import SessionLocal

from app.core.database_models import (
    Job,
    Candidate,
    ScreeningResult,
    ScreeningSkill,
)


def safe_list(value):

    if isinstance(value, list):
        return value

    if value is None:
        return []

    return [value]


def safe_float(value):

    if value is None:
        return None

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None


def extract_years(value):

    if value is None:
        return None

    if isinstance(
        value,
        (int, float),
    ):
        return float(value)

    match = re.search(
        r"\d+(?:\.\d+)?",
        str(value),
    )

    if not match:
        return None

    return float(
        match.group(0)
    )


def generate_uploaded_candidate_id(
    filename: str,
):

    """
    Generate a deterministic ID for an uploaded resume.

    The same filename produces the same ID, allowing
    the candidate record to be updated on repeated tests.
    """

    clean_filename = (
        str(filename)
        .strip()
        .lower()
    )

    digest = hashlib.sha256(
        clean_filename.encode(
            "utf-8"
        )
    ).hexdigest()[:12]

    return (
        f"UPLOAD_{digest}"
    )


def resolve_candidate_id(
    payload,
    screening,
):

    # --------------------------------------------------------
    # 1. Explicit candidate ID from API wrapper
    # --------------------------------------------------------

    candidate_id = (
        payload.get(
            "candidate_id"
        )
        if isinstance(
            payload,
            dict
        )
        else None
    )

    if candidate_id:
        return str(candidate_id)

    # --------------------------------------------------------
    # 2. Candidate ID directly inside screening
    # --------------------------------------------------------

    candidate_id = (
        screening.get(
            "candidate_id"
        )
        if isinstance(
            screening,
            dict
        )
        else None
    )

    if candidate_id:
        return str(candidate_id)

    # --------------------------------------------------------
    # 3. Candidate object
    # --------------------------------------------------------

    candidate_data = (
        screening.get(
            "candidate"
        )
        or {}
    )

    candidate_id = (
        candidate_data.get(
            "candidate_id"
        )
    )

    if candidate_id:
        return str(candidate_id)

    # --------------------------------------------------------
    # 4. Uploaded filename fallback
    # --------------------------------------------------------

    filename = (
        candidate_data.get(
            "filename"
        )
        or screening.get(
            "filename"
        )
        or "unknown_resume"
    )

    return generate_uploaded_candidate_id(
        filename
    )


def create_job(
    db,
    screening,
):

    job_data = (
        screening.get(
            "job"
        )
        or {}
    )

    title = (
        job_data.get(
            "title"
        )
        or "Untitled Job"
    )

    description = (
        job_data.get(
            "description"
        )
        or ""
    )

    required_skills = safe_list(
        job_data.get(
            "required_skills"
        )
    )

    preferred_skills = safe_list(
        job_data.get(
            "preferred_skills"
        )
    )

    required_education = safe_list(
        job_data.get(
            "required_education"
        )
    )

    experience = (
        screening.get(
            "experience"
        )
        or {}
    )

    required_experience = safe_float(
        experience.get(
            "required_years"
        )
    )

    if required_experience is None:

        required_experience = extract_years(
            job_data.get(
                "required_experience"
            )
        )

    # Reuse an identical job when possible.
    existing_job = db.scalar(
        select(Job)
        .where(
            Job.title == title,
            Job.description == description,
            Job.required_experience_years
            == required_experience,
        )
        .limit(1)
    )

    if existing_job is not None:
        return existing_job.id

    job = Job(
        title=title,
        description=description,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        required_experience_years=(
            required_experience
        ),
        required_education=(
            required_education
        ),
    )

    db.add(job)

    db.flush()

    return job.id


def save_candidate(
    db,
    candidate_id,
    screening,
):

    candidate_data = (
        screening.get(
            "candidate"
        )
        or {}
    )

    filename = (
        candidate_data.get(
            "filename"
        )
        or screening.get(
            "filename"
        )
        or "Unknown"
    )

    skills = safe_list(
        candidate_data.get(
            "skills"
        )
    )

    education = safe_list(
        candidate_data.get(
            "education"
        )
    )

    experience = (
        screening.get(
            "experience"
        )
        or {}
    )

    experience_years = safe_float(
        experience.get(
            "candidate_years"
        )
    )

    candidate = db.get(
        Candidate,
        str(candidate_id),
    )

    if candidate is None:

        candidate = Candidate(
            id=str(candidate_id),
            filename=filename,
            skills=skills,
            education=education,
            experience_years=(
                experience_years
            ),
        )

        db.add(candidate)

    else:

        candidate.filename = filename
        candidate.skills = skills
        candidate.education = education
        candidate.experience_years = (
            experience_years
        )

    db.flush()


def save_screening(
    db,
    candidate_id,
    screening,
    job_id,
    batch_id=None,
):

    pre_screen = (
        screening.get(
            "pre_screen"
        )
        or {}
    )

    model_scores = (
        screening.get(
            "model_scores"
        )
        or {}
    )

    row = ScreeningResult(
        batch_id=batch_id,

        job_id=job_id,

        candidate_id=str(
            candidate_id
        ),

        match_score=safe_float(
            screening.get(
                "match_score"
            )
        ),

        semantic_score=safe_float(
            model_scores.get(
                "semantic_score"
            )
        ),

        skill_score=safe_float(
            model_scores.get(
                "skill_score"
            )
        ),

        experience_score=safe_float(
            model_scores.get(
                "experience_score"
            )
        ),

        prescreen_status=(
            pre_screen.get(
                "status"
            )
            or "UNKNOWN"
        ),

        cluster=screening.get(
            "cluster"
        ),

        positive_factors=safe_list(
            screening.get(
                "positive_factors"
            )
        ),

        review_flags=safe_list(
            screening.get(
                "review_flags"
            )
        ),

        similar_resumes=safe_list(
            screening.get(
                "similar_resumes"
            )
        ),

        full_result=screening,
    )

    db.add(row)

    db.flush()

    screening_id = row.id

    skills = (
        screening.get(
            "skills"
        )
        or {}
    )

    for skill in safe_list(
        skills.get(
            "matched"
        )
    ):

        db.add(
            ScreeningSkill(
                screening_id=screening_id,
                skill_name=str(skill),
                skill_status="matched",
            )
        )

    for skill in safe_list(
        skills.get(
            "missing"
        )
    ):

        db.add(
            ScreeningSkill(
                screening_id=screening_id,
                skill_name=str(skill),
                skill_status="missing",
            )
        )

    return screening_id


def persist_screening_payload(
    payload,
):

    if SessionLocal is None:

        return {
            "saved": 0,
            "status": "DATABASE_NOT_CONFIGURED",
        }

    if not isinstance(
        payload,
        dict,
    ):

        return {
            "saved": 0,
            "status": "INVALID_PAYLOAD",
        }

    db = SessionLocal()

    saved_ids = []

    try:

        # ====================================================
        # BATCH RESPONSE
        # ====================================================

        if isinstance(
            payload.get(
                "results"
            ),
            list,
        ):

            batch_id = payload.get(
                "batch_id"
            )

            for item in payload.get(
                "results",
                [],
            ):

                if item.get(
                    "status"
                ) != "SUCCESS":

                    continue

                screening = (
                    item.get(
                        "screening"
                    )
                    or item.get(
                        "result"
                    )
                    or {}
                )

                candidate_id = resolve_candidate_id(
                    item,
                    screening,
                )

                job_id = create_job(
                    db,
                    screening,
                )

                save_candidate(
                    db,
                    candidate_id,
                    screening,
                )

                screening_id = save_screening(
                    db,
                    candidate_id,
                    screening,
                    job_id,
                    batch_id,
                )

                saved_ids.append(
                    screening_id
                )

        # ====================================================
        # SINGLE RESPONSE
        # ====================================================

        else:

            screening = (
                payload.get(
                    "screening"
                )
                or payload.get(
                    "result"
                )
                or payload
            )

            candidate_id = resolve_candidate_id(
                payload,
                screening,
            )

            job_id = create_job(
                db,
                screening,
            )

            save_candidate(
                db,
                candidate_id,
                screening,
            )

            screening_id = save_screening(
                db,
                candidate_id,
                screening,
                job_id,
                payload.get(
                    "batch_id"
                ),
            )

            saved_ids.append(
                screening_id
            )

        db.commit()

        return {
            "saved": len(
                saved_ids
            ),
            "screening_ids": saved_ids,
            "status": "SAVED",
        }

    except Exception:

        db.rollback()

        raise

    finally:

        db.close()
