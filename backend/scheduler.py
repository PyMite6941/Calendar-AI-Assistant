"""
Background scheduler for Calendar AI Assistant.
Runs the calendar crew on a fixed interval (default: every 10 minutes).

Usage — start from anywhere:
    from backend.scheduler import start, stop, status
    start()          # begins ticking every 600 s
    start(interval=60)  # custom interval in seconds
    stop()           # cancel cleanly
    status()         # {"running": bool, "interval_seconds": int, ...}

The scheduler is a daemon thread so it won't prevent the process from
exiting. Logs go to backend/storage/scheduler.log.
"""
import logging
import threading
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_LOG_PATH = _ROOT / "backend" / "storage" / "scheduler.log"
_DEFAULT_INTERVAL = 600  # 10 minutes

_stop_event = threading.Event()
_thread: threading.Thread | None = None
_interval: int = _DEFAULT_INTERVAL
_started_at: datetime | None = None


def _setup_logging():
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("calendar_scheduler")
    if not logger.handlers:
        handler = logging.FileHandler(_LOG_PATH, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def _run_crew(log):
    """Call the CrewAI pipeline with a periodic maintenance prompt."""
    try:
        from backend.agents.crew import run_calendar_assistant
        result = run_calendar_assistant(
            "Perform a periodic calendar check: "
            "(1) List any events happening in the next 2 hours. "
            "(2) List any todos that are due today or overdue. "
            "(3) Give a one-sentence summary of the day. "
            "Be brief and factual."
        )
        log.info(f"Crew OK — {str(result)[:300]}")
    except Exception as e:
        log.error(f"Crew error: {e}")


def _worker(interval: int):
    log = _setup_logging()
    log.info(f"Scheduler worker started — interval {interval}s")

    while not _stop_event.wait(interval):
        if _stop_event.is_set():
            break
        log.info(f"Tick at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        _run_crew(log)

    log.info("Scheduler worker stopped")


def start(interval: int = _DEFAULT_INTERVAL):
    """Start the background scheduler. Safe to call multiple times — only one thread runs."""
    global _thread, _interval, _started_at

    if _thread and _thread.is_alive():
        return  # already running

    _interval = interval
    _stop_event.clear()
    _started_at = datetime.now()

    _thread = threading.Thread(
        target=_worker,
        args=(interval,),
        name="calendar-scheduler",
        daemon=True,
    )
    _thread.start()

    log = _setup_logging()
    log.info(f"Scheduler started — interval {interval}s  pid {__import__('os').getpid()}")


def stop():
    """Stop the scheduler gracefully. Waits up to 2 s for the thread to exit."""
    global _thread
    _stop_event.set()
    if _thread and _thread.is_alive():
        _thread.join(timeout=2)
    _thread = None

    log = _setup_logging()
    log.info("Scheduler stopped by caller")


def status() -> dict:
    """Return current scheduler state as a plain dict (safe to JSON-serialise)."""
    running = bool(_thread and _thread.is_alive())
    return {
        "running": running,
        "interval_seconds": _interval,
        "started_at": _started_at.isoformat() if _started_at and running else None,
        "log_path": str(_LOG_PATH),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────
# python backend/scheduler.py --status
# python backend/scheduler.py --tick       (run one tick immediately and exit)

if __name__ == "__main__":
    import argparse
    import json
    import sys

    _p = argparse.ArgumentParser(description="Calendar AI Assistant scheduler")
    _p.add_argument("--status", action="store_true", help="Print scheduler status and exit")
    _p.add_argument("--tick",   action="store_true", help="Run one crew tick immediately and exit")
    _args = _p.parse_args()

    if _args.status:
        print(json.dumps(status(), indent=2))
        sys.exit(0)

    if _args.tick:
        _log = _setup_logging()
        from rich.console import Console as _Console
        _console = _Console()
        _console.print("[cyan]Running one scheduler tick…[/]")
        _run_crew(_log)
        _console.print(f"[green]Done. Log: {_LOG_PATH}[/]")
        sys.exit(0)

    _p.print_help()
