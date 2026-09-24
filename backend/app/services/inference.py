
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from app.core.model_loader import (
    get_model_bundle,
)

from app.services.resume_job_processing import (
    parse_resume,
    parse_job_description,
    normalize_skill,
)

from app.services.prescreen import (
    run_pre_screen,
)


# ============================================================
# Model bundle
# ============================================================

def _get_bundle():
    return get_model_bundle()


# ============================================================
# Text embedding
# ============================================================

def _normalize_embedding(
    embedding,
) -> np.ndarray:

    vector = np.asarray(
        embedding,
        dtype=np.float32,
    )

    norm = np.linalg.norm(
        vector
    )

    if norm == 0:
        return vector

    return vector / norm


def _embed_text(
    text: str,
) -> np.ndarray:

    bundle = _get_bundle()

    embedding = (
        bundle["embedding_model"]
        .encode(
            text or "",
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
    )

    return _normalize_embedding(
        embedding
    )


# ============================================================
# Skill helpers
# ============================================================

def _normalize_skill_name(
    skill: str,
) -> str:

    return normalize_skill(
        skill
    ).casefold().strip()


def calculate_skill_match(
    candidate_skills,
    required_skills,
):
    candidate_map = {
        _normalize_skill_name(skill): skill
        for skill in (
            candidate_skills or []
        )
        if _normalize_skill_name(skill)
    }

    required_map = {
        _normalize_skill_name(skill): skill
        for skill in (
            required_skills or []
        )
        if _normalize_skill_name(skill)
    }

    matched = []
    missing = []

    for key, original_skill in required_map.items():

        if key in candidate_map:
            matched.append(
                original_skill
            )
        else:
            missing.append(
                original_skill
            )

    required_count = len(
        required_map
    )

    matched_count = len(
        matched
    )

    if required_count == 0:
        skill_score = 1.0
    else:
        skill_score = (
            matched_count
            / required_count
        )

    return {
        "skill_score": float(
            skill_score
        ),
        "matched_skills": matched,
        "missing_skills": missing,
        "matched_skill_count": (
            matched_count
        ),
        "missing_skill_count": (
            len(missing)
        ),
    }


# ============================================================
# Experience score
# ============================================================

def calculate_experience_score(
    candidate_experience_years,
    required_experience_years,
):
    if required_experience_years is None:
        return 1.0

    if candidate_experience_years is None:
        return 0.0

    required = float(
        required_experience_years
    )

    candidate = float(
        candidate_experience_years
    )

    if required <= 0:
        return 1.0

    return float(
        min(
            candidate / required,
            1.0,
        )
    )


# ============================================================
# Model feature construction
# ============================================================

def build_model_features(
    semantic_score,
    skill_score,
    candidate_skill_count,
    job_skill_count,
    matched_skill_count,
    missing_skill_count,
    candidate_experience_years,
    required_experience_years,
    candidate_experience_missing,
    required_experience_missing,
):
    return {
        "semantic_score": float(
            semantic_score
        ),
        "skill_score": float(
            skill_score
        ),
        "candidate_skill_count": int(
            candidate_skill_count
        ),
        "job_skill_count": int(
            job_skill_count
        ),
        "matched_skill_count": int(
            matched_skill_count
        ),
        "missing_skill_count": int(
            missing_skill_count
        ),
        "experience_score": float(
            calculate_experience_score(
                candidate_experience_years,
                required_experience_years,
            )
        ),
        "candidate_experience_years": (
            None
            if candidate_experience_years
            is None
            else float(
                candidate_experience_years
            )
        ),
        "required_experience_years": (
            None
            if required_experience_years
            is None
            else float(
                required_experience_years
            )
        ),
        "candidate_experience_missing": int(
            bool(
                candidate_experience_missing
            )
        ),
        "required_experience_missing": int(
            bool(
                required_experience_missing
            )
        ),
    }


# ============================================================
# Random Forest prediction
# ============================================================

def predict_match_score(
    model_features,
) -> float:

    bundle = _get_bundle()

    feature_columns = list(
        bundle["feature_columns"]
    )

    imputation_values = (
        bundle["imputation_values"]
    )

    row = {}

    for column in feature_columns:

        value = model_features.get(
            column
        )

        if value is None:

            if column in imputation_values:
                value = imputation_values[
                    column
                ]

            else:
                value = 0.0

        row[column] = value

    frame = pd.DataFrame(
        [row],
        columns=feature_columns,
    )

    prediction = (
        bundle[
            "random_forest_model"
        ]
        .predict(frame)[0]
    )

    return float(
        np.clip(
            prediction,
            0.0,
            1.0,
        )
    )


# ============================================================
# KMeans cluster
# ============================================================

def predict_cluster(
    resume_embedding,
) -> int:

    bundle = _get_bundle()

    vector = np.asarray(
        resume_embedding,
        dtype=np.float32,
    ).reshape(
        1,
        -1,
    )

    cluster = (
        bundle["kmeans_model"]
        .predict(vector)[0]
    )

    return int(
        cluster
    )


# ============================================================
# FAISS similar resumes
# ============================================================

def _resume_identifier(
    record,
):
    if not isinstance(
        record,
        dict,
    ):
        return None

    for key in (
        "candidate_id",
        "resume_id",
        "id",
    ):
        value = record.get(
            key
        )

        if value is not None:
            return str(value)

    return None


def _resume_filename(
    record,
):
    if not isinstance(
        record,
        dict,
    ):
        return None

    for key in (
        "filename",
        "file_name",
        "resume_filename",
    ):
        value = record.get(
            key
        )

        if value:
            return str(value)

    return None


def find_similar_resumes(
    resume_embedding,
    top_k=5,
):
    bundle = _get_bundle()

    vector = np.asarray(
        resume_embedding,
        dtype=np.float32,
    ).reshape(
        1,
        -1,
    )

    vector = _normalize_embedding(
        vector[0]
    ).reshape(
        1,
        -1,
    )

    distances, indices = (
        bundle["faiss_index"]
        .search(
            vector,
            int(top_k),
        )
    )

    resumes = bundle[
        "resumes"
    ]

    results = []

    for similarity, index in zip(
        distances[0],
        indices[0],
    ):

        if index < 0:
            continue

        if index >= len(resumes):
            continue

        record = resumes[index]

        results.append({
            "index": int(index),
            "candidate_id": (
                _resume_identifier(
                    record
                )
            ),
            "filename": (
                _resume_filename(
                    record
                )
            ),
            "similarity": float(
                similarity
            ),
        })

    return results


# ============================================================
# Complete inference pipeline
# ============================================================

def run_inference(
    resume_file_content: bytes,
    resume_filename: str,
    job_description: str,
    job_title: str = "Untitled Job",
    similar_top_k: int = 5,
):
    # --------------------------------------------------------
    # Parse resume and job
    # --------------------------------------------------------

    resume = parse_resume(
        file_content=resume_file_content,
        filename=resume_filename,
    )

    job = parse_job_description(
        job_description=job_description,
        job_title=job_title,
    )

    # --------------------------------------------------------
    # Pre-screen
    # --------------------------------------------------------

    pre_screen = run_pre_screen(
        resume=resume,
        job=job,
    )

    # --------------------------------------------------------
    # Semantic similarity
    # --------------------------------------------------------

    resume_embedding = _embed_text(
        resume.get(
            "resume_text",
            "",
        )
    )

    job_embedding = _embed_text(
        job.get(
            "job_description",
            "",
        )
    )

    semantic_score = float(
        np.dot(
            resume_embedding,
            job_embedding,
        )
    )

    semantic_score = float(
        np.clip(
            semantic_score,
            0.0,
            1.0,
        )
    )

    # --------------------------------------------------------
    # Skill matching
    # --------------------------------------------------------

    skill_result = calculate_skill_match(
        candidate_skills=resume.get(
            "skills",
            [],
        ),
        required_skills=job.get(
            "required_skills",
            [],
        ),
    )

    skill_score = skill_result[
        "skill_score"
    ]

    # --------------------------------------------------------
    # Experience
    # --------------------------------------------------------

    candidate_experience_years = (
        resume.get(
            "experience_years"
        )
    )

    required_experience_years = (
        job.get(
            "required_experience_years"
        )
    )

    candidate_experience_missing = (
        resume.get(
            "experience_missing",
            candidate_experience_years is None,
        )
    )

    required_experience_missing = (
        required_experience_years is None
    )

    experience_score = (
        calculate_experience_score(
            candidate_experience_years,
            required_experience_years,
        )
    )

    # --------------------------------------------------------
    # Model features
    # --------------------------------------------------------

    model_features = build_model_features(
        semantic_score=semantic_score,
        skill_score=skill_score,
        candidate_skill_count=len(
            resume.get(
                "skills",
                [],
            )
        ),
        job_skill_count=len(
            job.get(
                "required_skills",
                [],
            )
        ),
        matched_skill_count=skill_result[
            "matched_skill_count"
        ],
        missing_skill_count=skill_result[
            "missing_skill_count"
        ],
        candidate_experience_years=(
            candidate_experience_years
        ),
        required_experience_years=(
            required_experience_years
        ),
        candidate_experience_missing=(
            candidate_experience_missing
        ),
        required_experience_missing=(
            required_experience_missing
        ),
    )

    # --------------------------------------------------------
    # Random Forest
    # --------------------------------------------------------

    match_score = predict_match_score(
        model_features
    )

    # --------------------------------------------------------
    # KMeans
    # --------------------------------------------------------

    cluster = predict_cluster(
        resume_embedding
    )

    # --------------------------------------------------------
    # Similar candidates
    # --------------------------------------------------------

    similar_resumes = (
        find_similar_resumes(
            resume_embedding,
            top_k=similar_top_k,
        )
    )

    return {
        "match_score": match_score,

        "match_score_percent": round(
            match_score * 100.0,
            2,
        ),

        "semantic_score": round(
            semantic_score,
            4,
        ),

        "skill_score": round(
            skill_score,
            4,
        ),

        "experience_score": round(
            experience_score,
            4,
        ),

        "matched_skills": skill_result[
            "matched_skills"
        ],

        "missing_skills": skill_result[
            "missing_skills"
        ],

        "matched_skill_count": (
            skill_result[
                "matched_skill_count"
            ]
        ),

        "missing_skill_count": (
            skill_result[
                "missing_skill_count"
            ]
        ),

        "candidate_experience_years": (
            candidate_experience_years
        ),

        "candidate_experience_display": (
            resume.get(
                "experience_display"
            )
        ),

        "required_experience_years": (
            required_experience_years
        ),

        "required_experience_display": (
            job.get(
                "required_experience"
            )
        ),

        "cluster": cluster,

        "similar_resumes": (
            similar_resumes
        ),

        "model_features": (
            model_features
        ),

        "pre_screen": pre_screen,

        "resume": resume,

        "job": job,
    }
