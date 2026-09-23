"""Tools available to the course agent.

Only `search_courses` is implemented locally. Web search is OpenAI's native
tool, wired in agent.py — there is deliberately no local web_search function.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from models import _DAY_TOKENS, Course

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA_PATH = ROOT / "data" / "yale_som_classes.json"

MAX_RESULTS = 15


@lru_cache(maxsize=1)
def load_courses() -> tuple[Course, ...]:
    """Parse and cache the course file as Course models."""
    rows = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return tuple(Course.model_validate(row) for row in rows)


def search_courses(
    query: str | None = None,
    faculty: str | None = None,
    category: str | None = None,
    day: str | None = None,
    limit: int = MAX_RESULTS,
) -> list[Course]:
    """Search the Yale SOM course catalog.

    Args:
        query: Free text matched against course number, title, description,
            category, faculty name, faculty bio, meeting times and room.
        faculty: Instructor name fragment, e.g. "Simonsohn" or "Uri".
        category: Course category fragment, e.g. "PhD", "Elective", "Core".
        day: Meeting day, e.g. "Wednesday", "Wed" or "We".
        limit: Maximum rows to return (hard-capped at 15).

    Returns:
        Matching courses, at most `limit` of them. An empty list means nothing
        in the catalog matched — say so rather than inventing a course.
    """
    courses = load_courses()
    raw_day = day.strip().lower() if day else ""
    wanted_day = _DAY_TOKENS.get(raw_day)
    results: list[Course] = []

    for course in courses:
        if query and query.strip().lower() not in course.haystack():
            continue
        if faculty and faculty.strip().lower() not in course.faculty.lower():
            continue
        if category and category.strip().lower() not in course.category.lower():
            continue
        if wanted_day:
            if wanted_day not in course.meeting_days():
                continue
        elif raw_day:
            # Unrecognized day string: fall back to the raw schedule text
            # rather than silently dropping the filter.
            if raw_day not in f"{course.day} {course.daytimes}".lower():
                continue
        results.append(course)

    capped = max(1, min(limit, MAX_RESULTS))
    return results[:capped]
