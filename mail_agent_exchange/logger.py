import os
import json
import time
from datetime import datetime, timezone

LOG_FILE   = os.getenv("LOG_FILE", "/app/logs/agents.jsonl")
AGENT_NAME = os.getenv("AGENT_NAME", "unknown-agent")

def _write(level: str, message: str, extra: dict | None = None):
    entry = {
        "ts":    datetime.now(timezone.utc).isoformat(),
        "epoch": time.time(),
        "agent": AGENT_NAME,
        "level": level,
        "msg":   message,
    }
    if extra:
        entry.update(extra)

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"[{entry['ts']}] [{level.upper()}] [{AGENT_NAME}] {message}", flush=True)

def log_info(message: str,  **extra): _write("info",  message, extra or None)
def log_warn(message: str,  **extra): _write("warn",  message, extra or None)
def log_error(message: str, **extra): _write("error", message, extra or None)
def log_debug(message: str, **extra): _write("debug", message, extra or None)