#!/usr/bin/env python3
"""Read the latest local Codex rate-limit event."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").expanduser()


def candidate_databases(codex_home: Path) -> list[Path]:
    return [
        codex_home / "sqlite" / "logs_2.sqlite",
        codex_home / "logs_2.sqlite",
    ]


def pick_database(codex_home: Path) -> Path:
    existing = [path for path in candidate_databases(codex_home) if path.exists()]
    if not existing:
        paths = ", ".join(str(path) for path in candidate_databases(codex_home))
        raise SystemExit(f"No Codex logs database found. Checked: {paths}")
    return max(existing, key=lambda path: path.stat().st_mtime)


def latest_rate_limit_event(db_path: Path, row_limit: int) -> tuple[int, dict[str, Any]]:
    decoder = json.JSONDecoder()
    marker = "websocket event: "
    uri = f"file:{db_path}?mode=ro"

    with sqlite3.connect(uri, uri=True) as con:
        rows = con.execute(
            """
            select ts, feedback_log_body
            from logs
            where feedback_log_body like ?
            order by ts desc, ts_nanos desc
            limit ?
            """,
            ("%websocket event:%", row_limit),
        )

        for ts, body in rows:
            index = body.find(marker)
            if index < 0:
                continue
            payload = body[index + len(marker) :]
            try:
                event, _ = decoder.raw_decode(payload)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "codex.rate_limits":
                return int(ts), event

    raise SystemExit("No codex.rate_limits event found in recent logs.")


def format_window(window: dict[str, Any]) -> dict[str, Any]:
    used = int(window["used_percent"])
    remaining = 100 - used
    reset_at = int(window["reset_at"])
    reset_dt = dt.datetime.fromtimestamp(reset_at).astimezone()
    return {
        "remaining_percent": remaining,
        "used_percent": used,
        "ui_remaining_percent": remaining,
        "api_used_percent": used,
        "window_minutes": int(window["window_minutes"]),
        "reset_after_seconds": int(window["reset_after_seconds"]),
        "reset_at": reset_at,
        "reset_at_local": reset_dt.strftime("%Y-%m-%d %H:%M:%S %Z"),
    }


def build_result(db_path: Path, ts: int, event: dict[str, Any]) -> dict[str, Any]:
    rate_limits = event["rate_limits"]
    captured_dt = dt.datetime.fromtimestamp(ts).astimezone()
    event_age_seconds = max(0, int(time.time()) - ts)
    return {
        "database": str(db_path),
        "captured_at": ts,
        "captured_at_local": captured_dt.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "event_age_seconds": event_age_seconds,
        "plan_type": event.get("plan_type"),
        "allowed": rate_limits.get("allowed"),
        "limit_reached": rate_limits.get("limit_reached"),
        "5h": format_window(rate_limits["primary"]),
        "weekly": format_window(rate_limits["secondary"]),
    }


def print_text(result: dict[str, Any]) -> None:
    print(f"captured_at: {result['captured_at_local']}")
    print(f"event_age_seconds: {result['event_age_seconds']}")
    print(f"plan_type: {result.get('plan_type')}")
    print(f"database: {result['database']}")
    for key, label in (("5h", "5 h"), ("weekly", "Semanal")):
        window = result[key]
        print(
            f"{label}: remaining {window['remaining_percent']}%, "
            f"used {window['used_percent']}%, renews {window['reset_at_local']}"
        )


def print_percentages(result: dict[str, Any]) -> None:
    lines = {
        "5h_remaining_percent": result["5h"]["ui_remaining_percent"],
        "5h_used_percent": result["5h"]["api_used_percent"],
        "5h_reset_at_local": result["5h"]["reset_at_local"],
        "weekly_remaining_percent": result["weekly"]["ui_remaining_percent"],
        "weekly_used_percent": result["weekly"]["api_used_percent"],
        "weekly_reset_at_local": result["weekly"]["reset_at_local"],
        "captured_at_local": result["captured_at_local"],
        "event_age_seconds": result["event_age_seconds"],
    }
    for key, value in lines.items():
        print(f"{key}={value}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--codex-home",
        default=str(default_codex_home()),
        help="Codex home directory. Defaults to CODEX_HOME or ~/.codex.",
    )
    parser.add_argument(
        "--db",
        help="Read this logs_2.sqlite file directly instead of auto-detecting under Codex home.",
    )
    parser.add_argument(
        "--row-limit",
        type=int,
        default=5000,
        help="Recent websocket log rows to inspect.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument(
        "--percentages",
        action="store_true",
        help="Print exact key=value percentage fields matching the Codex UI remaining values.",
    )
    parser.add_argument(
        "--fail-if-stale-seconds",
        type=int,
        help="Exit with an error if the latest codex.rate_limits event is older than this many seconds.",
    )
    args = parser.parse_args()

    db_path = Path(args.db).expanduser() if args.db else pick_database(Path(args.codex_home).expanduser())
    ts, event = latest_rate_limit_event(db_path, args.row_limit)
    result = build_result(db_path, ts, event)

    if args.fail_if_stale_seconds is not None and result["event_age_seconds"] > args.fail_if_stale_seconds:
        raise SystemExit(
            "Latest codex.rate_limits event is stale: "
            f"{result['event_age_seconds']}s > {args.fail_if_stale_seconds}s. "
            "Trigger a Codex model response and rerun."
        )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.percentages:
        print_percentages(result)
    else:
        print_text(result)


if __name__ == "__main__":
    main()
