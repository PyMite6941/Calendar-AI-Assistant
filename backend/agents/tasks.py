from crewai import Task

from .agents import (
    intent_analyzer,
    data_agent,
    processing_agent,
    verification_agent,
)

# All date/timezone/user values are injected at kickoff time via the inputs dict
# so the date stays correct for long-running processes.  Template vars used:
#   {today}       — "Monday, June 07, 2026"
#   {tz_ctx}      — "Timezone: Asia/Bangkok — current local time is 14:35."
#   {user_ctx}    — "The user's name is Matt.  Notification preferences: Email."  (or "")
#   {user_request}— the raw user message


analyze_request_task = Task(
    description="""\
Today is {today}. {tz_ctx}
{user_ctx}

Analyse the following user request:

{user_request}

Identify the intent (add event, add todo, query schedule, update item, delete item,
update user config/preference, general chat).
Extract all relevant details: dates, times, titles, locations, priorities, due dates, recurrence.
Convert any relative dates (e.g. "tomorrow", "next Monday", "in four days") to absolute dates
based on today's date and the timezone above.
If the request is about updating a user setting or preference (name, timezone, working hours,
notification preferences), identify it as a "set_config" intent and extract the key and value.
""",
    expected_output=(
        "A structured breakdown with: (1) intent type "
        "(add/update/delete/query/chat/set_config), "
        "(2) entity fields (title, start, end, location, priority, due_date, recurrence, "
        "config_key, config_value, etc.), "
        "(3) all relative dates converted to absolute YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS, "
        "(4) any stated assumptions where the message was ambiguous."
    ),
    agent=intent_analyzer,
)

retrieve_data_task = Task(
    description="""\
Today is {today}. {tz_ctx}
{user_ctx}

The original user request was: {user_request}

Using the intent analysis from the previous step, retrieve all calendar events and todo items
that are relevant to fulfilling the request.
- Use get_calendar_events to fetch local events.
- Use get_google_calendar_events to fetch events from Google Calendar (returns [] if not connected).
- Use get_todos to fetch todo items.
- Use get_gmail_messages if the request involves email context.
- Use get_config to read user preferences if needed.
Combine both local and Google Calendar results when answering schedule queries.
Only retrieve what is needed — do not dump everything if the request is narrow.
For set_config intents, skip data retrieval and pass through the key/value to the next step.
""",
    expected_output=(
        "The retrieved events and/or todos as structured data, with each item's index (for local items) "
        "or 'id' field (for Google Calendar items) clearly stated so the processing agent can reference "
        "them directly. If nothing relevant exists, state that explicitly. "
        "For set_config intents, confirm the key and value to be written."
    ),
    agent=data_agent,
    context=[analyze_request_task],
)

process_request_task = Task(
    description="""\
Today is {today}. {tz_ctx}
{user_ctx}

The original user request was: {user_request}

Using the intent analysis and the retrieved data from the previous steps, carry out the action:
- If adding a local event: call add_calendar_event with all relevant fields.
- If adding to Google Calendar: call add_google_calendar_event.
- If adding a todo: call add_todo with title, priority, due_date, and notes where available.
- If updating a local event/todo: call update_calendar_event or update_todo with the correct
  index and patch JSON.
- If updating a Google Calendar event: call update_google_calendar_event with the event 'id'.
- If deleting a local event/todo: call delete_calendar_event or delete_todo with the correct index.
- If deleting a Google Calendar event: call delete_google_calendar_event with the event 'id'.
- If updating a user preference (set_config intent): call set_config with the key and value.
- If answering a question: compose a clear, concise answer from the retrieved data.

Always use the resolved absolute dates from the analysis step.
Check that tool responses contain "ok": true before declaring success.
""",
    expected_output=(
        "One of: (a) confirmation that the write action was executed (tool output showing ok:true "
        "included), (b) a clear, factual answer to the user's question based on the retrieved data, "
        "or (c) confirmation that the config setting was updated. "
        "Must include the tool's return value for any write actions."
    ),
    agent=processing_agent,
    context=[analyze_request_task, retrieve_data_task],
)

verify_response_task = Task(
    description="""\
Today is {today}. {tz_ctx}
{user_ctx}

The original user request was: {user_request}

Review the output from the processing step:
- If an action was taken (add/update/delete/set_config), verify the tool returned ok:true
  and the action was correct.
- If a question was answered, verify the answer is accurate based on the retrieved data.
- Check for missing fields, wrong dates, or logical errors.
- If everything is correct, return the final response to the user.
- If something is wrong, describe what needs to be corrected.
""",
    expected_output=(
        "A single, final message in warm second-person language ('Your event has been added', "
        "'You have 3 todos due this week', 'Your name has been updated to Matt') that is "
        "accurate, concise, and ready to display verbatim. "
        "If something was wrong, a clear description of the error instead."
    ),
    agent=verification_agent,
    context=[process_request_task],
)
