
from __future__ import annotations

import re
from datetime import date
from typing import Optional


_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


_EDUCATION_HEADINGS = {
    "education",
    "academic",
    "academics",
    "academic background",
    "educational background",
    "qualifications",
    "qualification",
    "degrees",
    "degree",
    "certifications",
    "certification",
    "certificates",
    "school",
    "college",
    "university",
}


_SECTION_HEADINGS = {
    *_EDUCATION_HEADINGS,
    "work experience",
    "professional experience",
    "experience",
    "employment",
    "employment history",
    "career history",
    "professional summary",
    "summary",
    "profile",
    "objective",
    "about me",
    "skills",
    "technical skills",
    "projects",
    "languages",
    "awards",
    "achievements",
    "publications",
    "internships",
    "internship",
}


_MONTH_YEAR = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
    r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?)"
    r"\s+\d{4}"
)

_DATE_TOKEN = rf"(?:{_MONTH_YEAR}|\d{{4}})"

_RANGE_PATTERN = re.compile(
    rf"(?P<start>{_DATE_TOKEN})"
    rf"\s*(?:-|–|—|to|until|through)\s*"
    rf"(?P<end>"
    rf"present|current|now|till\s+date|to\s+date|{_DATE_TOKEN}"
    rf")",
    flags=re.IGNORECASE,
)

_EXPLICIT_YEARS_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b"
    r"(?:\s+of\s+(?:professional|relevant|total|work|"
    r"industry)\s+experience)?",
    flags=re.IGNORECASE,
)

_EXPLICIT_MONTHS_PATTERN = re.compile(
    r"\b(\d+)\s*(?:months?|mos?)\b",
    flags=re.IGNORECASE,
)


def _parse_date_token(token: str) -> tuple[int, int]:
    token = token.strip().lower()

    if token in {
        "present",
        "current",
        "now",
        "till date",
        "to date",
    }:
        today = date.today()
        return today.year, today.month

    parts = token.split()

    if len(parts) == 1:
        return int(parts[0]), 1

    month = _MONTHS.get(parts[0])
    if month is None:
        raise ValueError(
            f"Unsupported month token: {token}"
        )

    return int(parts[1]), month


def _month_index(year: int, month: int) -> int:
    return year * 12 + (month - 1)


def _nearest_section_heading(
    text: str,
    position: int,
) -> Optional[str]:

    lines_before = text[:position].splitlines()

    for line in reversed(lines_before):

        stripped = line.strip()

        if not stripped:
            continue

        cleaned = re.sub(
            r"^[\s\-•*#:|]+",
            "",
            stripped,
        )

        cleaned = re.sub(
            r"[\s:#|]+$",
            "",
            cleaned,
        )

        if not cleaned:
            continue

        normalized = re.sub(
            r"\s+",
            " ",
            cleaned,
        ).strip().lower()

        # Only recognize known resume section headings.
        # Do NOT treat arbitrary uppercase text such as
        # "BCA", company names, or job titles as headings.
        if normalized in _SECTION_HEADINGS:
            return normalized

    return None
def _is_education_context(
    text: str,
    position: int,
) -> bool:

    heading = _nearest_section_heading(
        text,
        position,
    )

    if heading is None:
        return False

    return (
        heading in _EDUCATION_HEADINGS
    )


def _extract_date_ranges(
    text: str,
) -> list[tuple[int, int]]:

    ranges = []

    today = date.today()
    current_month_index = _month_index(
        today.year,
        today.month,
    )

    for match in _RANGE_PATTERN.finditer(text):

        if _is_education_context(
            text,
            match.start(),
        ):
            continue

        start_year, start_month = _parse_date_token(
            match.group("start")
        )

        end_year, end_month = _parse_date_token(
            match.group("end")
        )

        start_index = _month_index(
            start_year,
            start_month,
        )

        end_index = _month_index(
            end_year,
            end_month,
        )

        # Completely future employment.
        if start_index > current_month_index:
            continue

        # Clip future end dates to current month.
        if end_index > current_month_index:
            end_index = current_month_index

        # Ignore invalid reversed ranges.
        if end_index < start_index:
            continue

        ranges.append(
            (start_index, end_index)
        )

    return ranges


def _merge_ranges(
    ranges: list[tuple[int, int]],
) -> list[tuple[int, int]]:

    if not ranges:
        return []

    ordered = sorted(ranges)
    merged = [ordered[0]]

    for start, end in ordered[1:]:

        prev_start, prev_end = merged[-1]

        # Overlapping or directly adjacent periods.
        if start <= prev_end + 1:
            merged[-1] = (
                prev_start,
                max(prev_end, end),
            )
        else:
            merged.append(
                (start, end)
            )

    return merged


def _extract_explicit_experience(
    text: str,
) -> Optional[float]:

    values = []

    for match in _EXPLICIT_YEARS_PATTERN.finditer(text):

        if _is_education_context(
            text,
            match.start(),
        ):
            continue

        value = float(match.group(1))

        if value > 0:
            values.append(value)

    if values:
        return max(values)

    month_values = []

    for match in _EXPLICIT_MONTHS_PATTERN.finditer(text):

        if _is_education_context(
            text,
            match.start(),
        ):
            continue

        value = int(match.group(1))

        if value > 0:
            month_values.append(value)

    if month_values:
        return max(month_values) / 12.0

    return None


def parse_experience(
    text: str,
) -> dict:

    if text is None:
        text = ""

    if not isinstance(text, str):
        raise TypeError(
            "Experience text must be a string"
        )

    text = text.strip()

    if not text:
        return {
            "experience_years": None,
            "experience_display": "Not specified",
            "experience_source": "missing",
            "experience_missing": True,
            "future_dated": False,
            "date_ranges": [],
        }

    # --------------------------------------------------------
    # Date-range calculation
    # --------------------------------------------------------

    raw_ranges = _extract_date_ranges(
        text
    )

    merged_ranges = _merge_ranges(
        raw_ranges
    )

    if merged_ranges:

        total_months = sum(
            end - start + 1
            for start, end in merged_ranges
        )

        years = total_months // 12
        months = total_months % 12

        if years and months:
            display = (
                f"{years} year"
                f"{'s' if years != 1 else ''} "
                f"{months} month"
                f"{'s' if months != 1 else ''}"
            )

        elif years:
            display = (
                f"{years} year"
                f"{'s' if years != 1 else ''}"
            )

        else:
            display = (
                f"{months} month"
                f"{'s' if months != 1 else ''}"
            )

        return {
            "experience_years": round(
                total_months / 12.0,
                4,
            ),
            "experience_display": display,
            "experience_source": "date_ranges",
            "experience_missing": False,
            "future_dated": False,
            "date_ranges": [
                {
                    "start_month_index": start,
                    "end_month_index": end,
                }
                for start, end in merged_ranges
            ],
        }

    # --------------------------------------------------------
    # Explicit phrase fallback
    # --------------------------------------------------------

    explicit_years = _extract_explicit_experience(
        text
    )

    if explicit_years is not None:

        total_months = round(
            explicit_years * 12
        )

        years = total_months // 12
        months = total_months % 12

        if years and months:
            display = (
                f"{years} year"
                f"{'s' if years != 1 else ''} "
                f"{months} month"
                f"{'s' if months != 1 else ''}"
            )

        elif years:
            display = (
                f"{years} year"
                f"{'s' if years != 1 else ''}"
            )

        else:
            display = (
                f"{months} month"
                f"{'s' if months != 1 else ''}"
            )

        return {
            "experience_years": round(
                explicit_years,
                4,
            ),
            "experience_display": display,
            "experience_source": "explicit_phrase",
            "experience_missing": False,
            "future_dated": False,
            "date_ranges": [],
        }

    # --------------------------------------------------------
    # Missing experience
    # --------------------------------------------------------

    return {
        "experience_years": None,
        "experience_display": "Not specified",
        "experience_source": "missing",
        "experience_missing": True,
        "future_dated": False,
        "date_ranges": [],
    }


def extract_experience(
    text: str,
) -> dict:
    return parse_experience(text)