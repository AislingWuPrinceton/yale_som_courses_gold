"""The Yale SOM course agent: pydantic-ai + gpt-6-astra through Portkey.

main.py imports `run_agent` from here and expects a dict shaped like
`{"reply": str, "tools_used": list[str]}`.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.capabilities import NativeTool
from pydantic_ai.messages import (
    NativeToolCallPart,
    NativeToolReturnPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.openai import (
    OpenAIResponsesModel,
    OpenAIResponsesModelSettings,
)
from pydantic_ai.native_tools import WebSearchTool
from pydantic_ai.providers.openai import OpenAIProvider

from models import AgentResult, AuditEntry, ToolCallRecord
from tools import search_courses

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROMPT_PATH = HERE / "prompts" / "prompt.md"
AUDIT_PATH = ROOT / "output" / "audit_trail.json"

# The key may sit in this lecture folder or any folder above it (the course
# root, e.g. MGT409/.env). Load every .env on the way up; nearest wins.
for _folder in (HERE, *ROOT.parents[::-1], ROOT):
    _candidate = _folder / ".env"
    if _candidate.is_file():
        load_dotenv(_candidate, override=True)

MODEL_NAME = "gpt-6-astra"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# The catalog tool keeps its own name; OpenAI's native web search reports
# under a provider-specific name, which we normalize to this for the UI.
WEB_SEARCH_LABEL = "web_search"


def _build_agent() -> Agent:
    api_key = os.environ.get("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError(
            "PORTKEY_API_KEY is not set. Put it in a .env file in this "
            "lecture folder or any folder above it (see .env.example)."
        )
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": api_key},
    )
    model = OpenAIResponsesModel(
        MODEL_NAME,
        provider=OpenAIProvider(openai_client=client),
    )
    return Agent(
        model,
        name="yale_som_course_agent",
        # Ask for reasoning summaries so the audit trail can record thoughts.
        model_settings=OpenAIResponsesModelSettings(
            openai_reasoning_summary="auto",
        ),
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
        tools=[search_courses],
        capabilities=[NativeTool(WebSearchTool())],
    )


_agent: Agent | None = None


def get_agent() -> Agent:
    """Build the agent once, lazily, so imports never need the API key."""
    global _agent
    if _agent is None:
        _agent = _build_agent()
    return _agent


def _short(value: Any, limit: int = 400) -> str:
    """Render a tool result as a short string for the audit trail."""
    if isinstance(value, (list, tuple)):
        text = f"{len(value)} item(s): " + json.dumps(
            [_label(v) for v in value[:5]], ensure_ascii=False, default=str
        )
    elif isinstance(value, (dict, str, int, float, bool)) or value is None:
        text = value if isinstance(value, str) else json.dumps(
            value, ensure_ascii=False, default=str
        )
    else:
        text = str(value)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "…"


def _label(item: Any) -> str:
    """One-line label for a course (or anything else) inside a result list."""
    number = getattr(item, "number", None)
    title = getattr(item, "title", None)
    if number or title:
        return f"{number} {title}".strip()
    return str(item)[:80]


def _as_dict(args: Any) -> dict[str, Any]:
    if isinstance(args, dict):
        return args
    if isinstance(args, str):
        try:
            parsed = json.loads(args)
        except json.JSONDecodeError:
            return {"raw": args}
        return parsed if isinstance(parsed, dict) else {"raw": parsed}
    return {} if args is None else {"raw": str(args)}


def _inspect_run(result: Any) -> tuple[list[str], list[ToolCallRecord], list[str], str]:
    """Pull thoughts, tool calls, tool names and a stop reason out of a run."""
    thoughts: list[str] = []
    calls: list[ToolCallRecord] = []
    tools_used: list[str] = []
    stop_reason = ""
    pending: dict[str, ToolCallRecord] = {}

    for message in result.all_messages():
        for part in getattr(message, "parts", []):
            if isinstance(part, ThinkingPart) and part.content:
                thoughts.append(part.content)

            elif isinstance(part, (ToolCallPart, NativeToolCallPart)):
                native = isinstance(part, NativeToolCallPart)
                name = WEB_SEARCH_LABEL if native else part.tool_name
                record = ToolCallRecord(tool=name, args=_as_dict(part.args))
                calls.append(record)
                if part.tool_call_id:
                    pending[part.tool_call_id] = record
                if name not in tools_used:
                    tools_used.append(name)

            elif isinstance(part, (ToolReturnPart, NativeToolReturnPart)):
                record = pending.get(part.tool_call_id)
                if record is not None:
                    record.result = _short(part.content)

        reason = getattr(message, "finish_reason", None)
        if reason:
            stop_reason = str(reason)

    return thoughts, calls, tools_used, stop_reason or "completed"


def _append_audit(entry: AuditEntry) -> None:
    """Append one row to output/audit_trail.json, never wiping earlier rows."""
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    if AUDIT_PATH.exists():
        try:
            loaded = json.loads(AUDIT_PATH.read_text(encoding="utf-8") or "[]")
            if isinstance(loaded, list):
                rows = loaded
            else:
                rows = [loaded]
        except json.JSONDecodeError:
            # Keep the unreadable file instead of destroying its contents.
            AUDIT_PATH.replace(AUDIT_PATH.with_suffix(".corrupt.json"))
            rows = []
    rows.append(entry.model_dump())
    AUDIT_PATH.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def run_agent(message: str) -> dict:
    """Run one agent loop and record it in the audit trail."""
    started = datetime.now(timezone.utc).isoformat()

    try:
        result = get_agent().run_sync(message)
    except Exception as exc:  # surface a readable error, never the API key
        entry = AuditEntry(
            time=started,
            user_message=message,
            reply="",
            stop_reason=f"error: {type(exc).__name__}",
        )
        _append_audit(entry)
        return AgentResult(
            reply=(
                "The course agent could not complete that request "
                f"({type(exc).__name__}). Please try again."
            ),
            tools_used=[],
        ).model_dump()

    thoughts, calls, tools_used, stop_reason = _inspect_run(result)
    reply = (result.output or "").strip()
    if not reply:
        reply = "".join(
            part.content
            for msg in result.all_messages()
            for part in getattr(msg, "parts", [])
            if isinstance(part, TextPart)
        ).strip()

    _append_audit(
        AuditEntry(
            time=started,
            user_message=message,
            thoughts=thoughts,
            tool_calls=calls,
            tools_used=tools_used,
            reply=reply,
            stop_reason=stop_reason,
        )
    )
    return AgentResult(reply=reply, tools_used=tools_used).model_dump()


if __name__ == "__main__":
    import sys

    question = " ".join(sys.argv[1:]) or "Who teaches Negotiations and when does it meet?"
    out = run_agent(question)
    print(out["reply"])
    print("\ntools_used:", out["tools_used"])
