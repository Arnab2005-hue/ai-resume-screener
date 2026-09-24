
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Any

from app.core.config import (
    MAX_BATCH_SIZE,
    MAX_FILE_SIZE_MB,
    SUPPORTED_RESUME_EXTENSIONS,
)

from app.services.resume_job_processing import (
    parse_resume,
)


MAX_FILE_SIZE_BYTES = int(
    MAX_FILE_SIZE_MB * 1024 * 1024
)


def _create_batch_id() -> str:
    return f"batch_{uuid.uuid4().hex}"


def _create_candidate_id() -> str:
    return f"cand_{uuid.uuid4().hex}"


def _calculate_sha256(
    file_content: bytes,
) -> str:

    return hashlib.sha256(
        file_content
    ).hexdigest()


def _validate_file(
    file_content: bytes,
    filename: str,
) -> None:

    if not isinstance(
        file_content,
        bytes,
    ):
        raise TypeError(
            "file_content must be bytes"
        )

    if not isinstance(
        filename,
        str,
    ):
        raise TypeError(
            "filename must be a string"
        )

    filename = filename.strip()

    if not filename:
        raise ValueError(
            "Filename cannot be empty"
        )

    extension = (
        Path(filename)
        .suffix
        .lower()
    )

    if extension not in SUPPORTED_RESUME_EXTENSIONS:
        raise ValueError(
            "Unsupported file type: "
            f"{extension or 'none'}"
        )

    if not file_content:
        raise ValueError(
            "File is empty"
        )

    if len(file_content) > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            "File exceeds maximum size of "
            f"{MAX_FILE_SIZE_MB:g} MB"
        )


def process_resume_batch(
    files: list[dict[str, Any]],
) -> dict[str, Any]:

    if not isinstance(
        files,
        list,
    ):
        raise TypeError(
            "files must be a list"
        )

    if not files:
        raise ValueError(
            "At least one resume is required"
        )

    if len(files) > MAX_BATCH_SIZE:
        raise ValueError(
            f"Maximum batch size is "
            f"{MAX_BATCH_SIZE} resumes"
        )

    batch_id = _create_batch_id()

    results = []

    seen_hashes = {}

    successful_count = 0
    failed_count = 0
    duplicate_count = 0

    for index, item in enumerate(files):

        filename = None

        try:

            if not isinstance(
                item,
                dict,
            ):
                raise TypeError(
                    "Each batch item must be a dictionary"
                )

            filename = item.get(
                "filename"
            )

            file_content = item.get(
                "file_content"
            )

            _validate_file(
                file_content=file_content,
                filename=filename,
            )

            sha256 = _calculate_sha256(
                file_content
            )

            # ------------------------------------------------
            # Duplicate detection
            # ------------------------------------------------

            if sha256 in seen_hashes:

                duplicate_count += 1

                results.append({
                    "index": index,
                    "filename": filename,
                    "status": "DUPLICATE",
                    "candidate_id": None,
                    "duplicate_of_candidate_id": (
                        seen_hashes[sha256]
                    ),
                    "sha256": sha256,
                    "resume": None,
                    "error": (
                        "Duplicate resume content"
                    ),
                })

                continue

            # ------------------------------------------------
            # API 4 parsing
            # ------------------------------------------------

            resume = parse_resume(
                file_content=file_content,
                filename=filename,
            )

            candidate_id = (
                _create_candidate_id()
            )

            resume[
                "candidate_id"
            ] = candidate_id

            resume[
                "batch_id"
            ] = batch_id

            resume[
                "sha256"
            ] = sha256

            seen_hashes[
                sha256
            ] = candidate_id

            successful_count += 1

            results.append({
                "index": index,
                "filename": filename,
                "status": "SUCCESS",
                "candidate_id": candidate_id,
                "duplicate_of_candidate_id": None,
                "sha256": sha256,
                "resume": resume,
                "error": None,
            })

        except Exception as exc:

            failed_count += 1

            results.append({
                "index": index,
                "filename": filename,
                "status": "FAILED",
                "candidate_id": None,
                "duplicate_of_candidate_id": None,
                "sha256": None,
                "resume": None,
                "error": str(exc),
            })

    return {
        "batch_id": batch_id,
        "total_files": len(files),
        "successful_count": successful_count,
        "failed_count": failed_count,
        "duplicate_count": duplicate_count,
        "results": results,
    }
