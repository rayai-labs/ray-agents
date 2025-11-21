# token_logger.py
"""
Simple, safe token usage logger for token-efficient-agent.

- Writes a JSON line per LLM invocation to /var/log/agent_token_usage.log (container)
- Keeps stored context small: record labels, model, token counts, and a few useful metadata fields.
- NEVER stores full prompts or raw dataset contents.
"""

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict

# Path inside the container/host to write logs. Can be mounted out in prod (or changed to /tmp).
LOG_PATH = os.getenv("AGENT_TOKEN_LOG_PATH", "/var/log/agent_token_usage.log")
Path(os.path.dirname(LOG_PATH) or ".").mkdir(parents=True, exist_ok=True)

def _safe_str(x: Any) -> str:
    try:
        return str(x)
    except Exception:
        return "<unserializable>"

def log_token_usage(llm_response: Dict, label: str, extra: Dict = None) -> None:
    """
    Log token usage from an LLM response.

    Parameters
    ----------
    llm_response : Dict
        The response object returned by the LLM client. Expected to contain a "usage" key
        similar to OpenAI-style responses:
            {"model": "...", "usage": {"prompt_tokens": n, "completion_tokens": m, "total_tokens": t}, ...}
        If "usage" is not present, will store best-effort numeric fields as 0.
    label : str
        Short label for where the call was made (e.g., "planner", "summarizer", "executor_prompt").
    extra : Dict, optional
        Small additional metadata (e.g., session_id, query_type). Values should be short strings/numbers.
    """
    if extra is None:
        extra = {}

    usage = llm_response.get("usage", {}) if isinstance(llm_response, dict) else {}
    try:
        record = {
            "time": datetime.utcnow().isoformat() + "Z",
            "label": _safe_str(label)[:128],
            "model": _safe_str(llm_response.get("model", "<unknown>"))[:128] if isinstance(llm_response, dict) else "<unknown>",
            "prompt_tokens": int(usage.get("prompt_tokens", 0)) if usage else 0,
            "completion_tokens": int(usage.get("completion_tokens", 0)) if usage else 0,
            "total_tokens": int(usage.get("total_tokens", 0)) if usage else 0,
            "latency_ms": int(extra.get("latency_ms", 0)) if extra else 0,
            # keep extra metadata short and explicitly stringified
            "session_id": _safe_str(extra.get("session_id", ""))[:128],
            "note": _safe_str(extra.get("note", ""))[:256],
        }
    except Exception:
        # Fallback minimal record to avoid crashes in production code paths
        record = {
            "time": datetime.utcnow().isoformat() + "Z",
            "label": _safe_str(label)[:128],
            "model": "<error>",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "latency_ms": 0,
            "session_id": "",
            "note": "failed to parse usage",
        }

    try:
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # If writing to /var/log fails (permission in local dev), fall back to a local file in cwd.
        fallback = Path("./agent_token_usage.log")
        try:
            with open(fallback, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            # Last-resort: silently ignore to avoid interrupting agent flow
            pass
