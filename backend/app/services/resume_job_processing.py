
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from functools import lru_cache
from typing import Optional

import re
import joblib
import pymupdf
from docx import Document

from app.core.config import (
    SKILL_NORMALIZATION_FILE,
    SUPPORTED_RESUME_EXTENSIONS,
)

from app.services.experience import (
    parse_experience,
)


# ============================================================
# Skill normalization
# ============================================================

@lru_cache(maxsize=1)
def _load_skill_normalization():

    if not SKILL_NORMALIZATION_FILE.exists():
        raise FileNotFoundError(
            "Skill normalization artifact not found: "
            f"{SKILL_NORMALIZATION_FILE}"
        )

    data = joblib.load(
        SKILL_NORMALIZATION_FILE
    )

    if not isinstance(data, dict):
        raise TypeError(
            "skill_normalization.pkl must contain a dictionary"
        )

    return data


@lru_cache(maxsize=1)
def _skill_aliases():

    raw = _load_skill_normalization()

    aliases = {}

    for key, value in raw.items():

        # alias -> canonical
        if isinstance(value, str):

            canonical = value.strip()

            if canonical:
                aliases[
                    str(key).strip().casefold()
                ] = canonical

                aliases[
                    canonical.casefold()
                ] = canonical

        # canonical -> aliases
        elif isinstance(
            value,
            (list, tuple, set),
        ):

            canonical = str(
                key
            ).strip()

            if not canonical:
                continue

            aliases[
                canonical.casefold()
            ] = canonical

            for item in value:

                alias = str(
                    item
                ).strip()

                if alias:
                    aliases[
                        alias.casefold()
                    ] = canonical

    return aliases


def _clean_skill(
    skill: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        skill.strip(),
    )


def normalize_skill(
    skill: str,
) -> str:

    cleaned = _clean_skill(
        skill
    )

    if not cleaned:
        return ""

    return _skill_aliases().get(
        cleaned.casefold(),
        cleaned,
    )


def extract_skills(
    text: str,
) -> list[str]:

    if not text:
        return []

    normalized_text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip().casefold()

    found = {}

    aliases = sorted(
        _skill_aliases().items(),
        key=lambda item: len(
            item[0]
        ),
        reverse=True,
    )

    for alias, canonical in aliases:

        if not alias:
            continue

        pattern = (
            r"(?<!\w)"
            + re.escape(alias)
            + r"(?!\w)"
        )

        if re.search(
            pattern,
            normalized_text,
        ):
            found[
                canonical.casefold()
            ] = canonical

    return sorted(
        found.values(),
        key=lambda value: value.casefold(),
    )


# ============================================================
# Document text extraction
# ============================================================

def extract_document_text(
    file_content: bytes,
    filename: str,
) -> str:

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

    extension = (
        Path(filename)
        .suffix
        .lower()
    )

    if extension not in SUPPORTED_RESUME_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {extension}"
        )

    # TXT
    if extension == ".txt":

        return file_content.decode(
            "utf-8",
            errors="replace",
        ).strip()

    # PDF
    if extension == ".pdf":

        text_parts = []

        with pymupdf.open(
            stream=file_content,
            filetype="pdf",
        ) as document:

            for page in document:
                text_parts.append(
                    page.get_text()
                )

        return "\n".join(
            text_parts
        ).strip()

    # DOCX
    if extension == ".docx":

        document = Document(
            BytesIO(file_content)
        )

        paragraphs = [
            paragraph.text
            for paragraph in document.paragraphs
        ]

        return "\n".join(
            paragraphs
        ).strip()

    raise ValueError(
        f"Unsupported file type: {extension}"
    )


# ============================================================
# Resume education
# ============================================================

_EDUCATION_PATTERNS = [
    (
        re.compile(
            r"\bBCA\b",
            re.IGNORECASE,
        ),
        "BCA",
    ),
    (
        re.compile(
            r"\bB\.?\s*Tech\b",
            re.IGNORECASE,
        ),
        "B.Tech",
    ),
    (
        re.compile(
            r"\bB\.?\s*E\.?\b",
            re.IGNORECASE,
        ),
        "B.E.",
    ),
    (
        re.compile(
            r"\bMCA\b",
            re.IGNORECASE,
        ),
        "MCA",
    ),
    (
        re.compile(
            r"\bM\.?\s*Tech\b",
            re.IGNORECASE,
        ),
        "M.Tech",
    ),
    (
        re.compile(
            r"\bM\.?\s*B\.?\s*A\b",
            re.IGNORECASE,
        ),
        "MBA",
    ),
    (
        re.compile(
            r"\bBachelor'?s?\s+degree\b",
            re.IGNORECASE,
        ),
        "Bachelor's Degree",
    ),
    (
        re.compile(
            r"\bMaster'?s?\s+degree\b",
            re.IGNORECASE,
        ),
        "Master's Degree",
    ),
    (
        re.compile(
            r"\bPh\.?\s*D\.?\b",
            re.IGNORECASE,
        ),
        "PhD",
    ),
]


def extract_education(
    text: str,
) -> list[str]:

    found = []

    for pattern, label in _EDUCATION_PATTERNS:

        if pattern.search(text):
            found.append(label)

    return list(
        dict.fromkeys(found)
    )


# ============================================================
# Resume parser
# ============================================================

def parse_resume(
    file_content: bytes,
    filename: str,
) -> dict:

    text = extract_document_text(
        file_content=file_content,
        filename=filename,
    )

    if not text:
        raise ValueError(
            "Resume document contains no readable text"
        )

    skills = extract_skills(
        text
    )

    education = extract_education(
        text
    )

    experience = parse_experience(
        text
    )

    extension = (
        Path(filename)
        .suffix
        .lower()
    )

    return {
        "filename": filename,
        "file_type": extension,

        "resume_text": text,

        "skills": skills,
        "skill_count": len(skills),

        "education": education,

        "experience_years": (
            experience[
                "experience_years"
            ]
        ),

        "experience_display": (
            experience[
                "experience_display"
            ]
        ),

        "experience": (
            experience[
                "experience_display"
            ]
        ),

        "experience_source": (
            experience[
                "experience_source"
            ]
        ),

        "experience_missing": (
            experience[
                "experience_missing"
            ]
        ),

        "future_dated": (
            experience[
                "future_dated"
            ]
        ),

        "experience_date_ranges": (
            experience[
                "date_ranges"
            ]
        ),
    }


# ============================================================
# Job description section headings
# ============================================================

_REQUIRED_HEADINGS = {
    "required skills",
    "required skill",
    "must have",
    "must-have",
    "must have skills",
    "must-have skills",
    "mandatory skills",
    "mandatory skill",
}


_PREFERRED_HEADINGS = {
    "preferred skills",
    "preferred skill",
    "nice to have",
    "nice-to-have",
    "nice to have skills",
    "good to have",
    "good to have skills",
    "bonus skills",
}


_OTHER_SECTION_HEADINGS = {
    "experience",
    "experience required",
    "required experience",
    "qualifications",
    "education",
    "requirements",
    "responsibilities",
    "job responsibilities",
    "about the role",
    "about the job",
    "description",
    "preferred qualifications",
}


def _normalize_heading(
    line: str,
) -> str:

    value = line.strip()

    value = re.sub(
        r"^[\s*#•\-\d.)]+",
        "",
        value,
    )

    value = re.sub(
        r"[\s*:]+$",
        "",
        value,
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip().casefold()


def _split_skill_sections(
    text: str,
) -> tuple[str, str]:

    required_lines = []
    preferred_lines = []

    current_section = None

    for line in text.splitlines():

        heading = _normalize_heading(
            line
        )

        if heading in _REQUIRED_HEADINGS:
            current_section = "required"
            continue

        if heading in _PREFERRED_HEADINGS:
            current_section = "preferred"
            continue

        if heading in _OTHER_SECTION_HEADINGS:
            current_section = None
            continue

        if current_section == "required":
            required_lines.append(line)

        elif current_section == "preferred":
            preferred_lines.append(line)

    return (
        "\n".join(
            required_lines
        ).strip(),

        "\n".join(
            preferred_lines
        ).strip(),
    )


def _extract_explicit_section_skills(
    section_text: str,
) -> list[str]:

    if not section_text.strip():
        return []

    skills = []

    for raw_line in section_text.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        # Remove bullet symbols.
        line = re.sub(
            r"^[\s\-•*▪◦‣]+",
            "",
            line,
        ).strip()

        # Remove numbered-list prefixes.
        line = re.sub(
            r"^\d+[\.)]\s*",
            "",
            line,
        ).strip()

        if not line:
            continue

        normalized_heading = _normalize_heading(
            line
        )

        if normalized_heading in (
            _REQUIRED_HEADINGS
            | _PREFERRED_HEADINGS
            | _OTHER_SECTION_HEADINGS
        ):
            continue

        # Preserve explicitly listed skills even when
        # they are absent from skill_normalization.pkl.
        skills.append(
            normalize_skill(line)
        )

    result = []
    seen = set()

    for skill in skills:

        cleaned = skill.strip()

        if not cleaned:
            continue

        key = cleaned.casefold()

        if key in seen:
            continue

        seen.add(key)
        result.append(cleaned)

    return result


# ============================================================
# Required experience
# ============================================================

_REQUIRED_EXPERIENCE_PATTERN = re.compile(
    r"(?:(?:minimum|at\s+least|required|"
    r"must\s+have|needs?|requires?)"
    r"\s*)?"
    r"(\d+(?:\.\d+)?)"
    r"\s*\+?\s*"
    r"(?:years?|yrs?)"
    r"(?:\s+of\s+"
    r"(?:professional|relevant|overall|work|industry)"
    r"\s+experience)?",
    re.IGNORECASE,
)


def extract_required_experience(
    text: str,
) -> Optional[float]:

    if not text:
        return None

    candidates = []

    for match in _REQUIRED_EXPERIENCE_PATTERN.finditer(
        text
    ):

        value = float(
            match.group(1)
        )

        if value <= 0:
            continue

        nearby = text[
            max(
                0,
                match.start() - 60,
            ):
            min(
                len(text),
                match.end() + 80,
            )
        ].casefold()

        priority = 1

        requirement_words = (
            "required",
            "minimum",
            "at least",
            "must have",
            "requires",
            "needs",
            "experience",
        )

        if any(
            word in nearby
            for word in requirement_words
        ):
            priority = 2

        candidates.append(
            (
                priority,
                value,
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item[0],
            item[1],
        ),
        reverse=True,
    )

    return candidates[0][1]


# ============================================================
# Required education
# ============================================================

_JOB_EDUCATION_PATTERNS = [
    (
        re.compile(
            r"\bBCA\b",
            re.IGNORECASE,
        ),
        "BCA",
    ),
    (
        re.compile(
            r"\bB\.?\s*Tech\b",
            re.IGNORECASE,
        ),
        "B.Tech",
    ),
    (
        re.compile(
            r"\bB\.?\s*E\.?\b",
            re.IGNORECASE,
        ),
        "B.E.",
    ),
    (
        re.compile(
            r"\bMCA\b",
            re.IGNORECASE,
        ),
        "MCA",
    ),
    (
        re.compile(
            r"\bM\.?\s*Tech\b",
            re.IGNORECASE,
        ),
        "M.Tech",
    ),
    (
        re.compile(
            r"\bM\.?\s*B\.?\s*A\b",
            re.IGNORECASE,
        ),
        "MBA",
    ),
    (
        re.compile(
            r"\bBachelor'?s?\s+degree\b",
            re.IGNORECASE,
        ),
        "Bachelor's Degree",
    ),
    (
        re.compile(
            r"\bMaster'?s?\s+degree\b",
            re.IGNORECASE,
        ),
        "Master's Degree",
    ),
]


def extract_required_education(
    text: str,
) -> list[str]:

    found = []

    for pattern, label in _JOB_EDUCATION_PATTERNS:

        if pattern.search(text):
            found.append(label)

    return list(
        dict.fromkeys(found)
    )


# ============================================================
# Job description parser
# ============================================================

def parse_job_description(
    job_description: str,
    job_title: Optional[str] = None,
) -> dict:

    if not isinstance(
        job_description,
        str,
    ):
        raise TypeError(
            "job_description must be a string"
        )

    if not job_description.strip():
        raise ValueError(
            "Job description cannot be empty"
        )

    text = job_description.strip()

    if job_title is None:
        job_title = "Untitled Job"

    (
        required_section,
        preferred_section,
    ) = _split_skill_sections(
        text
    )

    # Explicitly listed skills.
    required_skills = (
        _extract_explicit_section_skills(
            required_section
        )
    )

    preferred_skills = (
        _extract_explicit_section_skills(
            preferred_section
        )
    )

    # Fallback for a JD without an explicit required
    # skills section.
    if not required_skills:
        required_skills = extract_skills(
            text
        )

    # Preferred skills cannot also be required.
    preferred_keys = {
        skill.casefold()
        for skill in preferred_skills
    }

    required_skills = [
        skill
        for skill in required_skills
        if skill.casefold()
        not in preferred_keys
    ]

    required_skills = list(
        dict.fromkeys(
            required_skills
        )
    )

    preferred_skills = list(
        dict.fromkeys(
            preferred_skills
        )
    )

    required_experience = (
        extract_required_experience(
            text
        )
    )

    if required_experience is None:

        experience_display = (
            "Not specified"
        )

    elif float(
        required_experience
    ).is_integer():

        experience_display = (
            f"{int(required_experience)} years"
        )

    else:

        experience_display = (
            f"{required_experience:g} years"
        )

    required_education = (
        extract_required_education(
            text
        )
    )

    return {
        "job_title": job_title,

        "job_description": text,

        "required_skills": (
            required_skills
        ),

        "required_skill_count": (
            len(required_skills)
        ),

        "preferred_skills": (
            preferred_skills
        ),

        "preferred_skill_count": (
            len(preferred_skills)
        ),

        "required_experience": (
            experience_display
        ),

        "required_experience_years": (
            required_experience
        ),

        "required_education": (
            required_education
        ),
    }


# ============================================================
# Screening input
# ============================================================

def create_screening_input(
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

    return {
        "resume": resume,
        "job": job,
    }
