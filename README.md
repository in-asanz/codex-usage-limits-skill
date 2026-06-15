# Codex Usage Limits Skill

Codex skill for reading the current Codex usage/rate-limit percentages from local logs, without relying on screenshots.

It reports:

- 5-hour remaining percentage and renewal time
- weekly remaining percentage and renewal time
- used percentage for both windows
- source `logs_2.sqlite` database and capture timestamp

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

## How It Works

Codex emits local websocket log events named `codex.rate_limits`. The skill reads the newest event from `logs_2.sqlite`, then converts stored `used_percent` values into the UI-style remaining percentage:

```text
remaining_percent = 100 - used_percent
```

The 5-hour window is `rate_limits.primary`; the weekly window is `rate_limits.secondary`.

The API currently exposes percentage values as integer `used_percent` fields. The script returns those exact API integers and computes the UI remaining value as `100 - used_percent`. It also reports `event_age_seconds` so callers can reject stale local events.

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

## Requirements

- Python 3.9+
- Python standard library `sqlite3`

No third-party packages are required.
