"""Pydantic models shared by the agent, its tools, and the audit trail."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# Day tokens appearing in "Timings Day" (Mo,We) and "Daytimes" (M  W / T  Th),
# matched exactly so "T" (Tuesday) never collides with "Th" (Thursday).
_DAY_TOKENS = {
    "m": "monday", "mo": "monday", "mon": "monday", "monday": "monday",
    "t": "tuesday", "tu": "tuesday", "tue": "tuesday", "tues": "tuesday",
    "tuesday": "tuesday",
    "w": "wednesday", "we": "wednesday", "wed": "wednesday",
    "wednesday": "wednesday",
    "th": "thursday", "thu": "thursday", "thur": "thursday",
    "thurs": "thursday", "thursday": "thursday",
    "f": "friday", "fr": "friday", "fri": "friday", "friday": "friday",
    "sa": "saturday", "sat": "saturday", "saturday": "saturday",
    "su": "sunday", "sun": "sunday", "sunday": "sunday",
}


class Course(BaseModel):
    """One row of data/yale_som_classes.json.

    Field aliases are the exact JSON keys, so `Course.model_validate(row)` works
    on the raw file and `model_dump(by_alias=True)` round-trips back to it.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    course_id: str = Field(default="", alias="Course ID")
    number: str = Field(default="", alias="Course Number")
    title: str = Field(default="", alias="Course Title")
    description: str = Field(default="", alias="Course Description")
    category: str = Field(default="", alias="Course Category")
    course_type: str = Field(default="", alias="Course Type")
    section: str = Field(default="", alias="Section")
    units: str = Field(default="", alias="Units")

    session: str = Field(default="", alias="Course Session")
    session_start: str = Field(default="", alias="Course Session Start date")
    session_end: str = Field(default="", alias="Course Session End Date")
    term_code: str = Field(default="", alias="TermCode")

    daytimes: str = Field(default="", alias="Daytimes")
    day: str = Field(default="", alias="Timings Day")
    start_time: str = Field(default="", alias="Timings StartTime")
    end_time: str = Field(default="", alias="Timings EndTime")
    room: str = Field(default="", alias="Room")

    faculty: str = Field(default="", alias="Faculty 1")
    faculty_email: str = Field(default="", alias="Faculty 1 Email")
    faculty_bio: str = Field(default="", alias="faculty_bio")

    syllabus: str = Field(default="", alias="Syllabus")
    old_syllabus: str = Field(default="", alias="Old Syllabus")
    bid_or_permission: str = Field(default="", alias="Bid Or Permission")
    visible: str = Field(default="", alias="Visible")

    def meeting_days(self) -> set[str]:
        """Canonical weekday names this course meets.

        Reads the structured "Timings Day" field when present (Mo,We) and
        otherwise falls back to the day letters leading "Daytimes" (M  W),
        which is the only day signal on most rows.
        """
        tokens = re.split(r"[\s,]+", self.day.strip())
        if not any(tokens):
            head = re.split(r"\d", self.daytimes.strip(), maxsplit=1)[0]
            tokens = re.split(r"[\s,]+", head.strip())
        return {
            _DAY_TOKENS[t.lower()] for t in tokens if t and t.lower() in _DAY_TOKENS
        }

    def haystack(self) -> str:
        """Lowercased text used for free-text matching."""
        return " ".join(
            (
                self.number,
                self.title,
                self.description,
                self.category,
                self.course_type,
                self.faculty,
                self.faculty_bio,
                self.daytimes,
                self.day,
                self.room,
                self.session,
            )
        ).lower()


class AgentResult(BaseModel):
    """What run_agent() hands back to main.py."""

    reply: str = ""
    tools_used: list[str] = Field(default_factory=list)


class ToolCallRecord(BaseModel):
    """One tool invocation inside a single agent loop."""

    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    result: str = ""


class AuditEntry(BaseModel):
    """One appended row of output/audit_trail.json."""

    time: str
    user_message: str
    thoughts: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    reply: str = ""
    stop_reason: str = ""
