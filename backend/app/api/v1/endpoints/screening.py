
from __future__ import annotations

from typing import List

from fastapi import (
    APIRouter,
    File,
    Form,
    UploadFile,
    HTTPException,
)

from app.services.batch_processing import (
    process_resume_batch,
)

from app.services.explainability import (
    screen_with_explanation,
)

from app.services.prescreen import (
    pre_screen_resume,
)


router = APIRouter(
    prefix="/api/v1",
    tags=["Screening"],
)


# ============================================================
# Pre-screen
# ============================================================

@router.post("/prescreen")
async def prescreen_endpoint(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    job_title: str = Form("Untitled Job"),
):
    try:
        file_content = await resume.read()

        return pre_screen_resume(
            file_content=file_content,
            filename=resume.filename or "resume.txt",
            job_description=job_description,
            job_title=job_title,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


# ============================================================
# Full screening
# ============================================================

@router.post("/screen")
async def screen_endpoint(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    job_title: str = Form("Untitled Job"),
    similar_top_k: int = Form(5),
):
    if similar_top_k < 1 or similar_top_k > 20:
        raise HTTPException(
            status_code=400,
            detail="similar_top_k must be between 1 and 20",
        )

    try:
        file_content = await resume.read()

        return screen_with_explanation(
            resume_file_content=file_content,
            resume_filename=resume.filename or "resume.txt",
            job_description=job_description,
            job_title=job_title,
            similar_top_k=similar_top_k,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


# ============================================================
# Batch screening
# ============================================================

@router.post("/batch-screen")
async def batch_screen_endpoint(
    resumes: List[UploadFile] = File(...),
    job_description: str = Form(...),
    job_title: str = Form("Untitled Job"),
    similar_top_k: int = Form(5),
):
    if similar_top_k < 1 or similar_top_k > 20:
        raise HTTPException(
            status_code=400,
            detail="similar_top_k must be between 1 and 20",
        )

    try:
        files = []

        for upload in resumes:
            files.append({
                "filename": (
                    upload.filename
                    or "resume.txt"
                ),
                "file_content": (
                    await upload.read()
                ),
            })

        batch_result = process_resume_batch(
            files
        )

        screening_results = []

        for item in batch_result["results"]:

            if item["status"] != "SUCCESS":
                screening_results.append({
                    "index": item["index"],
                    "filename": item["filename"],
                    "status": item["status"],
                    "candidate_id": item.get(
                        "candidate_id"
                    ),
                    "error": item.get(
                        "error"
                    ),
                    "duplicate_of_candidate_id": (
                        item.get(
                            "duplicate_of_candidate_id"
                        )
                    ),
                    "screening": None,
                })

                continue

            original_file = files[
                item["index"]
            ]

            screening = screen_with_explanation(
                resume_file_content=(
                    original_file[
                        "file_content"
                    ]
                ),
                resume_filename=(
                    original_file[
                        "filename"
                    ]
                ),
                job_description=job_description,
                job_title=job_title,
                similar_top_k=similar_top_k,
            )

            screening_results.append({
                "index": item["index"],
                "filename": item["filename"],
                "status": "SUCCESS",
                "candidate_id": item[
                    "candidate_id"
                ],
                "error": None,
                "duplicate_of_candidate_id": None,
                "screening": screening,
            })

        return {
            "batch_id": batch_result[
                "batch_id"
            ],
            "total_files": batch_result[
                "total_files"
            ],
            "successful_count": batch_result[
                "successful_count"
            ],
            "failed_count": batch_result[
                "failed_count"
            ],
            "duplicate_count": batch_result[
                "duplicate_count"
            ],
            "results": screening_results,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )
