# Codex Usage Limits Skill

Codex skill for reading the current Codex usage/rate-limit percentages from local logs, without relying on screenshots.

It reports:

- 5-hour remaining percentage and renewal time
- weekly remaining percentage and renewal time
- used percentage for both windows
- source SQLite database or session JSONL file and capture timestamp
- optional banked/free Codex reset credits and expiry dates, only when explicitly requested

## Requirements

- Codex installed and used at least once, so local Codex logs exist.
- Python 3 with the standard-library `sqlite3` module.

No third-party packages are required. No OpenAI API key is required.

The optional reset-credit mode uses your existing Codex ChatGPT session in `~/.codex/auth.json` and calls an internal ChatGPT endpoint. It does not print tokens or account IDs.

## Install

Copy the skill folder into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R codex-usage-limits ~/.codex/skills/
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.codex\skills"
Copy-Item -Recurse -Force ".\codex-usage-limits" "$env:USERPROFILE\.codex\skills\"
```

## Run Directly

Linux/macOS:

```bash
sh ~/.codex/skills/codex-usage-limits/scripts/codex_usage_limits.sh
```

Windows PowerShell:

```powershell
& "$env:USERPROFILE\.codex\skills\codex-usage-limits\scripts\codex_usage_limits.ps1"
```

JSON output:

```bash
python3 ~/.codex/skills/codex-usage-limits/scripts/codex_usage_limits.py --json
```

Exact key/value percentage output:

```bash
python3 ~/.codex/skills/codex-usage-limits/scripts/codex_usage_limits.py --percentages
```

Example:

```text
5h_remaining_percent=70
5h_used_percent=30
weekly_remaining_percent=80
weekly_used_percent=20
```

Fail when the latest local rate-limit event is stale:

```bash
python3 ~/.codex/skills/codex-usage-limits/scripts/codex_usage_limits.py --percentages --fail-if-stale-seconds 300
```

Banked/free Codex reset credits:

```bash
python3 ~/.codex/skills/codex-usage-limits/scripts/codex_usage_limits.py --reset-credits
```

Windows PowerShell:

```powershell
& "$env:USERPROFILE\.codex\skills\codex-usage-limits\scripts\codex_usage_limits.ps1" -ResetCredits
```

Example:

```text
available_count: 3
available_listed: 3
1. status=available reset_type=codex_rate_limits granted=2026-06-18 02:34:13 Hora de verano romance expires=2026-07-18 02:34:13 Hora de verano romance
```

## Why This Skill

This skill is intentionally local and narrow:

- Default usage-percentage mode does not read `auth.json`.
- Default usage-percentage mode does not read credentials or tokens.
- Default usage-percentage mode does not call private OpenAI/ChatGPT usage endpoints.
- It does not require an API key.
- It reads local Codex rate-limit events from `logs_2.sqlite` and newer `sessions/**/*.jsonl` files.
- It works as a Codex skill and as a direct script.

Reset-credit mode is separate and opt-in. It reads the existing Codex auth session and calls:

```text
https://chatgpt.com/backend-api/wham/rate-limit-reset-credits
```

This endpoint is not a public stable API. Use it as a practical workaround for `available_count`, `granted_at`, and `expires_at`, and expect it may change.

Similar public tools often call private usage endpoints, inspect auth material, or provide a broader multi-provider dashboard. This project keeps the default path focused on reproducing the Codex "usage remaining" percentages from local `codex.rate_limits` events; reset credits are an explicit opt-in path.

## How It Works

Codex emits local events named `codex.rate_limits`. The skill reads the newest event from `logs_2.sqlite` and newer session JSONL files, then converts stored `used_percent` values into the UI-style remaining percentage:

```text
remaining_percent = 100 - used_percent
```

The 5-hour window is `rate_limits.primary`; the weekly window is `rate_limits.secondary`.

The API currently exposes percentage values as integer `used_percent` fields. The script returns those exact API integers and computes the UI remaining value as `100 - used_percent`. It also reports `event_age_seconds` so callers can reject stale local events.

If the API starts emitting decimal percentages, the script preserves them instead of truncating. The `--percentages` mode prints the exact string value, and JSON output includes `*_percent_exact` fields alongside numeric compatibility fields.

For reset credits, the script reads the internal reset-credit response, keeps only sanitized fields, and prints available credits with local grant/expiry times. It deliberately avoids printing tokens, raw headers, or raw account IDs.

## Platform Support

- Windows: supported via Python or `scripts/codex_usage_limits.ps1`.
- Linux/macOS: supported via Python or `scripts/codex_usage_limits.sh`.
- Codex App and Codex terminal/CLI are supported when they write local logs under the selected Codex home.

If Codex uses a non-default home directory:

```bash
python3 codex-usage-limits/scripts/codex_usage_limits.py --codex-home /path/to/.codex
```

Or read a database directly:

```bash
python3 codex-usage-limits/scripts/codex_usage_limits.py --db /path/to/logs_2.sqlite
```

## Privacy

Do not publish your `.codex` directory, SQLite logs, auth files, credentials, screenshots, or local output containing private data. This repository contains only the skill code and documentation.
