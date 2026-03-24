import json
import os
import threading
from datetime import datetime, timezone

LOG_FILE = os.getenv("LOG_FILE", "/app/logs/agents.jsonl")
AGENT_NAME = os.getenv("AGENT_NAME", "unknown")

_lock = threading.Lock()

def _ensure_dir():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log(message: str, level: str = "INFO", **extra):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent": AGENT_NAME,
        "level": level,
        "msg": message,
        **extra
    }
    line = json.dumps(entry, ensure_ascii=False)
    print(line, flush=True)
    try:
        _ensure_dir()
        with _lock:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception as e:
        print(f"[logger] Impossible d'écrire dans {LOG_FILE}: {e}", flush=True)

def log_info(msg, **kw):  log(msg, "INFO",  **kw)
def log_warn(msg, **kw):  log(msg, "WARN",  **kw)
def log_error(msg, **kw): log(msg, "ERROR", **kw)
