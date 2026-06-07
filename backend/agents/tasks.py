import tomllib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from crewai import Task

from .agents import (
    intent_analyzer,
    data_agent,
    processing_agent,
    verification_agent,
)

_ROOT = Path(__file__).resolve().parents[2]


def _load_user_tz() -> tuple[str, ZoneInfo]:
    try:
        with open(_ROOT / "backend/storage/configs.toml", "rb") as f:
            tz_name = tomllib.load(f).get("timezone") or "UTC"
    except Exception:
        tz_name = "UTC"
    try:
        return tz_name, ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return "UTC", ZoneInfo("UTC")


_TZ_NAME, _TZ = _load_user_tz()
_NOW   = datetime.now(_TZ)
_TODAY = _NOW.strftime("%A, %B %d, %Y")
_TIME  = _NOW.strftime("%H:%M")
_TZ_CTX = f"Timezone: {_TZ_NAME} — current local time is {_TIME}."


analyze_request_task = Task(
    description=f"""
Today is {_TODAY}. {_TZ_CTX}

Analyse the following user request:

{{user_request}}

Identify the intent (add event, add todo, query schedule, update item, delete item, general chat).
Extract all relevant details: dates, times, titles, locations, priorities, due dates, recurrence.
Convert any relative dates (e.g. "tomorrow", "next Monday", "in four days") to absolute dates
based on today's date and the timezone above.
""",
    expected_output=(
        "A structured breakdown with: (1) intent type (add/update/delete/query/chat), "
        "(2) entity fields (title, start, end, location, priority, due_date, recurrence, etc.), "
        "(3) all relative dates converted to absolute YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS, "
        "(4) any stated assumptions where the message was ambiguous."
    ),
    agent=intent_analyzer,
)

retrieve_data_task = Task(
    description=f"""
Today is {_TODAY}. {_TZ_CTX}

The original user request was: {{user_request}}

Using the intent analysis from the previous step, retrieve all calendar events and todo items
that are relevant to fulfilling the request.
- Use get_calendar_events to fetch local events.
- Use get_google_calendar_events to fetch events from Google Calendar (returns [] if not connected).
- Use get_todos to fetch todo items.
- Use get_gmail_messages if the request involves email context.
- Use get_config to read user preferences such as user_name or timezone if helpful.
Combine both local and Google Calendar results when answering schedule queries.
Only retrieve what is needed — do not dump everything if the request is narrow.
""",
    expected_output=(
        "The retrieved events and/or todos as structured data, with each item's index (for local items) "
        "or 'id' field (for Google Calendar items) clearly stated so the processing agent can reference "
        "them directly. If nothing relevant exists, state that explicitly."
    ),
    agent=data_agent,
    context=[analyze_request_task],
)

process_request_task = Task(
    description=f"""
Today is {_TODAY}. {_TZ_CTX}

The original user request was: {{user_request}}

Using the intent analysis and the retrieved data from the previous steps, carry out the appropriate action:
- If adding a local event: call add_calendar_event with all relevant fields.
- If adding to Google Calendar: call add_google_calendar_event (use when user mentions Google or for synced events).
- If adding a todo: call add_todo with title, priority, due_date, and notes where available.
- If updating a local event/todo: call update_calendar_event or update_todo with the correct index and patch JSON.
- If updating a Google Calendar event: call update_google_calendar_event with the event 'id' and patch JSON.
- If deleting a local event/todo: call delete_calendar_event or delete_todo with the correct index.
- If deleting a Google Calendar event: call delete_google_calendar_event with the event 'id'.
- If answering a question: compose a clear, concise answer from the retrieved data.

Always use the resolved absolute dates from the analysis step.
Check that tool responses contain "ok": true before declaring success.
""",
    expected_output=(
        "One of: (a) confirmation that the write action was executed (tool output showing ok:true included), "
        "(b) a clear, factual answer to the user's question based on the retrieved data. "
        "Must include the tool's return value for any write actions."
    ),
    agent=processing_agent,
    context=[analyze_request_task, retrieve_data_task],
)

verify_response_task = Task(
    description=f"""
Today is {_TODAY}. {_TZ_CTX}

The original user request was: {{user_request}}

Review the output from the processing step:
- If an action was taken (add/update/delete), verify the tool returned ok:true and the action was correct.
- If a question was answered, verify the answer is accurate based on the retrieved data.
- Check for missing fields, wrong dates, or logical errors.
- If everything is correct, return the final response to the user.
- If something is wrong, describe what needs to be corrected.
""",
    expected_output=(
        "A single, final message in warm second-person language ('Your event has been added', "
        "'You have 3 todos due this week') that is accurate, concise, and ready to display verbatim. "
        "If something was wrong, a clear description of the error instead."
    ),
    agent=verification_agent,
    context=[process_request_task],
)
