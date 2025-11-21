# examples/analyzer/token_efficient_agent/tools/aggregate_tokens.py
"""
Aggregate token logger output into a CSV summary.

Reads agent_token_usage.log (fallback local file) and writes token_summary.csv
containing averages per (label, model).
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

# Matches fallback used by token_logger
LOG_PATHS = [
    Path("/var/log/agent_token_usage.log"),
    Path("agent_token_usage.log"),
    Path("examples/analyzer/token_efficient_agent/agent_token_usage.log"),
]

OUT_CSV = Path("token_summary.csv")

def find_log_path():
    for p in LOG_PATHS:
        if p.exists():
            return p
    # If nothing found, raise
    raise FileNotFoundError(f"No token log found. Tried: {', '.join(str(p) for p in LOG_PATHS)}")

def aggregate(logfile_path: Path | None = None, out_csv: Path | None = None):
    logfile = logfile_path or find_log_path()
    out_csv = out_csv or OUT_CSV

    stats = defaultdict(lambda: {"count": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    with open(logfile, "r", encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
                key = (r.get("label", "unknown"), r.get("model", "unknown"))
                stats[key]["count"] += 1
                stats[key]["prompt_tokens"] += int(r.get("prompt_tokens", 0))
                stats[key]["completion_tokens"] += int(r.get("completion_tokens", 0))
                stats[key]["total_tokens"] += int(r.get("total_tokens", 0))
            except Exception:
                continue

    with open(out_csv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["label", "model", "count", "avg_prompt_tokens", "avg_completion_tokens", "avg_total_tokens"])
        for (label, model), v in stats.items():
            c = v["count"]
            writer.writerow([
                label,
                model,
                c,
                round(v["prompt_tokens"] / c, 2) if c else 0,
                round(v["completion_tokens"] / c, 2) if c else 0,
                round(v["total_tokens"] / c, 2) if c else 0,
            ])
    print(f"Wrote summary to {out_csv} (from {logfile})")

if __name__ == "__main__":
    aggregate()
