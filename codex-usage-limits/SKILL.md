---
name: codex-usage-limits
description: Inspect local Codex usage/rate-limit percentages without screenshots. Use when the user asks for current Codex usage, remaining usage, weekly percentage, 5-hour percentage, reset time, renewal time, or how to obtain the Codex UI "Uso restante" values from local state/logs.
---

# Codex Usage Limits

## Purpose

Obtain the same values shown by Codex "Uso restante" without using an image. Codex stores rate-limit events locally as `codex.rate_limits` websocket events.

## Scope

Use this for Codex App and Codex terminal/CLI when they write local logs under the same Codex home directory. The Python script is cross-platform and defaults to `CODEX_HOME` or `~/.codex`.

This method depends on local log availability, not on the UI. If Codex terminal uses a different `CODEX_HOME`, pass it with `--codex-home`. If the logs do not contain a recent `codex.rate_limits` event, trigger a Codex model response first and rerun the script.

## Quick Command

On Windows PowerShell:

```powershell
& "$env:USERPROFILE\.codex\skills\codex-usage-limits\scripts\codex_usage_limits.ps1"
```

On Linux/macOS:

```bash
sh ~/.codex/skills/codex-usage-limits/scripts/codex_usage_limits.sh
```

Run the Python script directly when wrappers are not available:

```powershell
python "$env:USERPROFILE\.codex\skills\codex-usage-limits\scripts\codex_usage_limits.py"
```

```bash
python3 ~/.codex/skills/codex-usage-limits/scripts/codex_usage_limits.py
```

Use JSON when the result will be consumed by another script:

```powershell
& "$env:USERPROFILE\.codex\skills\codex-usage-limits\scripts\codex_usage_limits.ps1" -Json
```

```bash
sh ~/.codex/skills/codex-usage-limits/scripts/codex_usage_limits.sh --json
```

Use exact machine-readable percentage fields:

```powershell
& "$env:USERPROFILE\.codex\skills\codex-usage-limits\scripts\codex_usage_limits.ps1" -Percentages
```

```bash
sh ~/.codex/skills/codex-usage-limits/scripts/codex_usage_limits.sh --percentages
```

Require a fresh event, for example not older than 5 minutes:

```bash
python3 ~/.codex/skills/codex-usage-limits/scripts/codex_usage_limits.py --percentages --fail-if-stale-seconds 300
```

## Manual Steps

1. Locate the active Codex logs database. Prefer the newest existing file among:
   - `%USERPROFILE%\.codex\sqlite\logs_2.sqlite`
   - `%USERPROFILE%\.codex\logs_2.sqlite`
   - `$HOME/.codex/sqlite/logs_2.sqlite`
   - `$HOME/.codex/logs_2.sqlite`
2. Open it read-only with SQLite.
3. Query recent log rows containing `websocket event:`.
4. Parse the JSON payload after `websocket event: ` with `json.JSONDecoder().raw_decode(...)`; rows can contain suffix text.
5. Select the newest event where `type == "codex.rate_limits"`.
6. Read:
   - `rate_limits.primary`: 5-hour window.
   - `rate_limits.secondary`: weekly window.
7. Convert the stored used percentage to UI remaining percentage:
   - `remaining_percent = 100 - used_percent`
8. Convert `reset_at` from Unix seconds to local time. That is when the window renews.

## Field Meaning

- `primary.window_minutes == 300`: 5-hour limit.
- `secondary.window_minutes == 10080`: weekly limit.
- `used_percent`: percentage already consumed.
- `api_used_percent`: same API value, exposed explicitly.
- UI "Uso restante": `100 - used_percent`.
- `ui_remaining_percent`: exact value to compare with the UI percentage.
- `reset_after_seconds`: seconds until renewal from the event timestamp.
- `reset_at`: absolute renewal timestamp.
- `event_age_seconds`: age of the local `codex.rate_limits` event. If it is too old, trigger a new Codex model response and rerun.

## Validation

After running the script, compare:

- `5h.remaining_percent` with the UI row labeled `5 h`.
- `weekly.remaining_percent` with the UI row labeled `Semanal`.
- `reset_at_local` with the UI renewal time/date.

If values are stale, start a new Codex interaction or wait for the next model response; `codex.rate_limits` is emitted by the API stream and the local log only updates after such events.

## Platform Notes

- Windows: use `scripts/codex_usage_limits.ps1` or `python scripts/codex_usage_limits.py`.
- Linux/macOS: use `scripts/codex_usage_limits.sh` or `python3 scripts/codex_usage_limits.py`.
- If `CODEX_HOME` differs between Codex App and Codex terminal, pass `--codex-home <path>` on Python/Linux or `-CodexHome <path>` on PowerShell.
- If Python is installed as `python` instead of `python3` on Linux, the shell wrapper falls back automatically.
