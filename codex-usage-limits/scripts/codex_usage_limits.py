#!/usr/bin/env python3
"""Read the latest local Codex rate-limit event."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sqlite3
import time
from decimal import Decimal
from pathlib import Path
from typing import Any


LOG_PATTERNS = (
    ("%websocket event:%", "websocket event: "),
    ("%Received message {%", "Received message "),
)
SESSION_FILE_LIMIT = 80


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


def decode_event(decoder: json.JSONDecoder, body: str) -> dict[str, Any] | None:
    for marker in ("websocket event: ", "Received message "):
        index = body.find(marker)
        if index < 0:
            continue
        payload = body[index + len(marker) :].lstrip()
        if not payload.startswith("{"):
            continue
        try:
            event, _ = decoder.raw_decode(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            return event
    return None


def normalize_window(window: dict[str, Any], ts: int) -> dict[str, Any]:
    reset_at = int(window.get("reset_at", window.get("resets_at")))
    return {
        "used_percent": window["used_percent"],
        "window_minutes": window["window_minutes"],
        "reset_at": reset_at,
        "reset_after_seconds": int(window.get("reset_after_seconds", max(0, reset_at - ts))),
    }


def normalize_rate_limit_event(ts: int, rate_limits: dict[str, Any]) -> dict[str, Any]:
    limit_reached = bool(rate_limits.get("rate_limit_reached_type"))
    return {
        "type": "codex.rate_limits",
        "plan_type": rate_limits.get("plan_type"),
        "rate_limits": {
            "allowed": not limit_reached,
            "limit_reached": limit_reached,
            "primary": normalize_window(rate_limits["primary"], ts),
            "secondary": normalize_window(rate_limits["secondary"], ts),
        },
    }


def parse_iso_timestamp(value: str) -> int:
    return int(dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def latest_rate_limit_event_from_db(db_path: Path, row_limit: int) -> tuple[int, dict[str, Any], str]:
    decoder = json.JSONDecoder(parse_float=Decimal, parse_int=Decimal)
    uri = f"file:{db_path}?mode=ro"

    with sqlite3.connect(uri, uri=True) as con:
        candidates: list[tuple[int, int, str]] = []
        for pattern, _marker in LOG_PATTERNS:
            rows = con.execute(
                """
                select ts, ts_nanos, feedback_log_body
                from logs
                where feedback_log_body like ?
                order by ts desc, ts_nanos desc
                limit ?
                """,
                (pattern, row_limit),
            )
            candidates.extend((int(ts), int(ts_nanos), body or "") for ts, ts_nanos, body in rows)

        for ts, _ts_nanos, body in sorted(candidates, key=lambda item: (item[0], item[1]), reverse=True):
            event = decode_event(decoder, body)
            if event and event.get("type") == "codex.rate_limits":
                return ts, event, str(db_path)

    raise SystemExit("No codex.rate_limits event found in recent logs.")


def latest_rate_limit_event_from_sessions(codex_home: Path, row_limit: int) -> tuple[int, dict[str, Any], str] | None:
    sessions_dir = codex_home / "sessions"
    if not sessions_dir.exists():
        return None

    decoder = json.JSONDecoder(parse_float=Decimal, parse_int=Decimal)
    files = sorted(sessions_dir.rglob("*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)[:SESSION_FILE_LIMIT]
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in reversed(lines[-row_limit:]):
            if '"rate_limits"' not in line:
                continue
            try:
                item, _ = decoder.raw_decode(line)
            except json.JSONDecodeError:
                continue
            payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
            rate_limits = item.get("rate_limits") or payload.get("rate_limits")
            if not isinstance(rate_limits, dict) or rate_limits.get("limit_id") != "codex":
                continue
            return parse_iso_timestamp(item["timestamp"]), normalize_rate_limit_event(parse_iso_timestamp(item["timestamp"]), rate_limits), str(path)
    return None


def latest_rate_limit_event(codex_home: Path, db_path: Path, row_limit: int, include_sessions: bool) -> tuple[int, dict[str, Any], str]:
    candidates = [latest_rate_limit_event_from_db(db_path, row_limit)]
    if include_sessions:
        session_event = latest_rate_limit_event_from_sessions(codex_home, row_limit)
        if session_event:
            candidates.append(session_event)
    return max(candidates, key=lambda item: item[0])


def decimal_value(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def format_decimal(value: Decimal) -> str:
    if value == value.to_integral_value():
        return str(int(value))
    return format(value.normalize(), "f")


def json_percent(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def format_window(window: dict[str, Any]) -> dict[str, Any]:
    used = decimal_value(window["used_percent"])
    remaining = Decimal("100") - used
    reset_at = int(window["reset_at"])
    reset_dt = dt.datetime.fromtimestamp(reset_at).astimezone()
    return {
        "remaining_percent": json_percent(remaining),
        "used_percent": json_percent(used),
        "ui_remaining_percent": json_percent(remaining),
        "api_used_percent": json_percent(used),
        "remaining_percent_exact": format_decimal(remaining),
        "used_percent_exact": format_decimal(used),
        "ui_remaining_percent_exact": format_decimal(remaining),
        "api_used_percent_exact": format_decimal(used),
        "window_minutes": int(window["window_minutes"]),
        "reset_after_seconds": int(window["reset_after_seconds"]),
        "reset_at": reset_at,
        "reset_at_local": reset_dt.strftime("%Y-%m-%d %H:%M:%S %Z"),
    }


def stale_reason(ts: int, rate_limits: dict[str, Any]) -> str | None:
    now = int(time.time())
    if now < ts:
        return None
    for label, window in (("5h", rate_limits["primary"]), ("weekly", rate_limits["secondary"])):
        reset_at = int(window["reset_at"])
        if ts < reset_at <= now:
            return f"latest {label} event belongs to a previous reset window"
    return None


def build_result(db_path: Path, source: str, ts: int, event: dict[str, Any]) -> dict[str, Any]:
    rate_limits = event["rate_limits"]
    captured_dt = dt.datetime.fromtimestamp(ts).astimezone()
    event_age_seconds = max(0, int(time.time()) - ts)
    reason = stale_reason(ts, rate_limits)
    return {
        "database": str(db_path),
        "source": source,
        "captured_at": ts,
        "captured_at_local": captured_dt.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "event_age_seconds": event_age_seconds,
        "data_fresh": reason is None,
        "stale_reason": reason,
        "plan_type": event.get("plan_type"),
        "allowed": rate_limits.get("allowed"),
        "limit_reached": rate_limits.get("limit_reached"),
        "5h": format_window(rate_limits["primary"]),
        "weekly": format_window(rate_limits["secondary"]),
    }


def print_text(result: dict[str, Any]) -> None:
    print(f"captured_at: {result['captured_at_local']}")
    print(f"event_age_seconds: {result['event_age_seconds']}")
    print(f"data_fresh: {result['data_fresh']}")
    if result.get("stale_reason"):
        print(f"stale_reason: {result['stale_reason']}")
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
        "5h_remaining_percent": result["5h"]["ui_remaining_percent_exact"],
        "5h_used_percent": result["5h"]["api_used_percent_exact"],
        "5h_reset_at_local": result["5h"]["reset_at_local"],
        "weekly_remaining_percent": result["weekly"]["ui_remaining_percent_exact"],
        "weekly_used_percent": result["weekly"]["api_used_percent_exact"],
        "weekly_reset_at_local": result["weekly"]["reset_at_local"],
        "captured_at_local": result["captured_at_local"],
        "event_age_seconds": result["event_age_seconds"],
        "data_fresh": str(result["data_fresh"]).lower(),
        "stale_reason": result.get("stale_reason") or "",
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
    codex_home = Path(args.codex_home).expanduser()
    ts, event, source = latest_rate_limit_event(codex_home, db_path, args.row_limit, include_sessions=args.db is None)
    result = build_result(db_path, source, ts, event)

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
