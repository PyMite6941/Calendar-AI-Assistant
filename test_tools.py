"""
Subprocess tool tests for Calendar AI Assistant.
Run from the project root:  python test_tools.py
"""
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).resolve().parent
console = Console()

# Use the venv Python if present, otherwise fall back to the running interpreter.
_VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"          # Windows
if not _VENV_PY.exists():
    _VENV_PY = ROOT / ".venv" / "bin" / "python"              # Linux / macOS
PYTHON = str(_VENV_PY) if _VENV_PY.exists() else sys.executable

# ── helpers ───────────────────────────────────────────────────────────────────

def run(*cmd, input_text=None, timeout=15):
    # Replace bare "python" with the resolved interpreter
    resolved = [PYTHON if c == "python" else c for c in cmd]
    result = subprocess.run(
        resolved, cwd=str(ROOT),
        capture_output=True, text=True, input=input_text,
        timeout=timeout,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def tmp_json(content):
    f = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
    json.dump(content, f)
    f.close()
    return f.name

def tmp_toml(content=""):
    f = tempfile.NamedTemporaryFile(suffix=".toml", delete=False, mode="w")
    f.write(content)
    f.close()
    return f.name

def ollama_running():
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return True
    except Exception:
        return False

# ── test registry ─────────────────────────────────────────────────────────────

_results = []

def test(name):
    def decorator(fn):
        try:
            fn()
            _results.append(("PASS", name, ""))
        except AssertionError as e:
            _results.append(("FAIL", name, str(e)))
        except Exception as e:
            _results.append(("FAIL", name, f"{type(e).__name__}: {e}"))
        return fn
    return decorator

def skip(name, reason):
    _results.append(("SKIP", name, reason))

# ── calendar_events.py ────────────────────────────────────────────────────────

@test("calendar_events --get returns valid JSON list")
def _():
    code, out, err = run("python", "backend/tools/calendar_events.py", "--get")
    assert code == 0, f"exit {code}  stderr: {err}"
    data = json.loads(out)
    assert isinstance(data, list), f"expected list, got {type(data).__name__}"

@test("calendar_events --add writes event to file")
def _():
    path = tmp_json([])
    try:
        code, out, err = run(
            "python", "backend/tools/calendar_events.py",
            "--add", "Test Meeting", "2026-06-06T10:00:00", "2026-06-06T11:00:00",
            "--path", path,
        )
        assert code == 0, f"exit {code}  stderr: {err}"
        events = json.loads(Path(path).read_text())
        assert any(e["title"] == "Test Meeting" for e in events), \
            f"event not found in: {events}"
    finally:
        os.unlink(path)

@test("calendar_events --save round-trips JSON")
def _():
    path = tmp_json([])
    payload = json.dumps([{"title": "Saved", "start": "2026-01-01", "end": "2026-01-01"}])
    try:
        code, out, err = run(
            "python", "backend/tools/calendar_events.py",
            "--save", payload, "--path", path,
        )
        assert code == 0, f"exit {code}  stderr: {err}"
        events = json.loads(Path(path).read_text())
        assert events[0]["title"] == "Saved", f"unexpected: {events}"
    finally:
        os.unlink(path)

# ── todo_stuff.py ─────────────────────────────────────────────────────────────

@test("todo_stuff --get returns valid JSON list")
def _():
    code, out, err = run("python", "backend/tools/todo_stuff.py", "--get")
    assert code == 0, f"exit {code}  stderr: {err}"
    data = json.loads(out)
    assert isinstance(data, list), f"expected list, got {type(data).__name__}"

@test("todo_stuff --add writes todo to file")
def _():
    path = tmp_json([])
    try:
        code, out, err = run(
            "python", "backend/tools/todo_stuff.py",
            "--add", "Write tests", "Make sure everything works",
            "--path", path,
        )
        assert code == 0, f"exit {code}  stderr: {err}"
        todos = json.loads(Path(path).read_text())
        assert any(t["title"] == "Write tests" for t in todos), \
            f"todo not found in: {todos}"
    finally:
        os.unlink(path)

@test("todo_stuff --delete removes item by index")
def _():
    path = tmp_json([
        {"title": "Keep me",   "description": ""},
        {"title": "Delete me", "description": ""},
    ])
    try:
        code, out, err = run(
            "python", "backend/tools/todo_stuff.py",
            "--delete", "1", "--path", path,
        )
        assert code == 0, f"exit {code}  stderr: {err}"
        todos = json.loads(Path(path).read_text())
        assert len(todos) == 1, f"expected 1 item, got {len(todos)}"
        assert todos[0]["title"] == "Keep me", f"wrong item remains: {todos}"
    finally:
        os.unlink(path)

@test("todo_stuff --delete out-of-range exits 0 with error message")
def _():
    path = tmp_json([{"title": "Only one", "description": ""}])
    try:
        code, out, err = run(
            "python", "backend/tools/todo_stuff.py",
            "--delete", "99", "--path", path,
        )
        # should not crash hard — just print an error
        assert code == 0, f"exit {code}  stderr: {err}"
    finally:
        os.unlink(path)

# ── config_editing.py ─────────────────────────────────────────────────────────

@test("config_editing --set / --key roundtrip")
def _():
    path = tmp_toml("")
    try:
        code, _, err = run(
            "python", "backend/tools/config_editing.py",
            "--key", "test_key", "--set", "hello_world", "--path", path,
        )
        assert code == 0, f"set exit {code}  stderr: {err}"

        code2, out2, err2 = run(
            "python", "backend/tools/config_editing.py",
            "--key", "test_key", "--path", path,
        )
        assert code2 == 0, f"get exit {code2}  stderr: {err2}"
        assert out2 == "hello_world", f"expected 'hello_world', got '{out2}'"
    finally:
        os.unlink(path)

@test("config_editing --read returns without error")
def _():
    code, out, err = run(
        "python", "backend/tools/config_editing.py", "--read",
    )
    assert code == 0, f"exit {code}  stderr: {err}"
    # empty config is valid — just must not crash

@test("config_editing --delete removes key")
def _():
    path = tmp_toml('remove_me = "bye"\n')
    try:
        code, _, err = run(
            "python", "backend/tools/config_editing.py",
            "--delete", "remove_me", "--path", path,
        )
        assert code == 0, f"exit {code}  stderr: {err}"
        code2, out2, _ = run(
            "python", "backend/tools/config_editing.py",
            "--key", "remove_me", "--default", "GONE", "--path", path,
        )
        assert out2 == "GONE", f"key still present: '{out2}'"
    finally:
        os.unlink(path)

# ── add_google_oauth.py ───────────────────────────────────────────────────────

@test("add_google_oauth --status returns valid JSON with 'connected' key")
def _():
    code, out, err = run(
        "python", "backend/auth/add_google_oauth.py", "--status",
    )
    assert code == 0, f"exit {code}  stderr: {err}"
    data = json.loads(out)
    assert "connected" in data, f"missing 'connected' key: {data}"

@test("add_google_oauth --list-events returns JSON when not connected")
def _():
    # Should return an error dict, not crash
    code, out, err = run(
        "python", "backend/auth/add_google_oauth.py", "--list-events",
    )
    # exit 1 is valid when not connected; output must still be JSON
    data = json.loads(out)
    assert isinstance(data, (list, dict)), f"non-JSON output: {out}"

# ── agent imports ─────────────────────────────────────────────────────────────

@test("backend.agents.agents imports without error")
def _():
    code, out, err = run(
        "python", "-c",
        "from backend.agents.agents import ("
        "intent_analyzer, data_agent, processing_agent, verification_agent, planner_agent"
        "); print('ok')",
        timeout=30,
    )
    assert code == 0, f"exit {code}  stderr: {err}"
    assert "ok" in out

@test("backend.agents.crew imports and exposes run_calendar_assistant")
def _():
    code, out, err = run(
        "python", "-c",
        "from backend.agents.crew import run_calendar_assistant; print('ok')",
        timeout=30,
    )
    assert code == 0, f"exit {code}  stderr: {err}"
    assert "ok" in out

@test("backend.agents.tasks imports without error")
def _():
    code, out, err = run(
        "python", "-c",
        "from backend.agents.tasks import ("
        "analyze_request_task, retrieve_data_task, "
        "process_request_task, verify_response_task"
        "); print('ok')",
        timeout=30,
    )
    assert code == 0, f"exit {code}  stderr: {err}"
    assert "ok" in out

# ── connect_to_ai.py (LLM — skip if no provider available) ───────────────────

_OLLAMA_TEST = "connect_to_ai --ask responds via Ollama (LLM live test)"
if ollama_running():
    try:
        _r = subprocess.run(
            [PYTHON, "backend/tools/connect_to_ai.py", "--ask", "Say hi", "--provider", "ollama"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=90,
        )
        if _r.returncode == 0 and _r.stdout.strip():
            _results.append(("PASS", _OLLAMA_TEST, ""))
        else:
            _results.append(("FAIL", _OLLAMA_TEST,
                             f"exit {_r.returncode}  stderr: {_r.stderr.strip()[:200]}"))
    except subprocess.TimeoutExpired:
        skip(_OLLAMA_TEST, "Ollama server up but model inference timed out (>90 s) — model may not be loaded")
else:
    skip(_OLLAMA_TEST, "Ollama not running on localhost:11434")

# ── scheduler ─────────────────────────────────────────────────────────────────

@test("backend.scheduler imports and status() returns dict")
def _():
    code, out, err = run(
        "python", "-c",
        "from backend.scheduler import status; import json; print(json.dumps(status()))",
    )
    assert code == 0, f"exit {code}  stderr: {err}"
    data = json.loads(out)
    assert "running" in data, f"missing 'running' key: {data}"
    assert data["running"] is False, "scheduler should not be running before start()"

# ── results ───────────────────────────────────────────────────────────────────

table = Table(title="Calendar AI Assistant — Tool Tests", show_header=True, header_style="bold")
table.add_column("", width=5, no_wrap=True)
table.add_column("Test", style="cyan")
table.add_column("Detail", style="dim")

passed = failed = skipped = 0
for status_str, name, detail in _results:
    if status_str == "PASS":
        table.add_row("[green]PASS[/]", name, detail)
        passed += 1
    elif status_str == "SKIP":
        table.add_row("[yellow]SKIP[/]", name, detail)
        skipped += 1
    else:
        table.add_row("[red]FAIL[/]", name, detail)
        failed += 1

console.print(table)
console.print(
    f"\n[bold]{passed + failed + skipped} tests:[/]  "
    f"[green]{passed} passed[/]  "
    f"[red]{failed} failed[/]  "
    f"[yellow]{skipped} skipped[/]"
)
sys.exit(0 if failed == 0 else 1)
