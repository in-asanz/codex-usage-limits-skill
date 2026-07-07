---
name: codex-usage-limits
description: Inspect Codex usage/rate-limit percentages and optional banked reset credits without screenshots. Use when the user asks for current Codex usage, remaining usage, weekly percentage, 5-hour percentage, reset time, renewal time, Codex UI "Uso restante" values from local state/logs, or available/free Codex reset credits and their expiry dates.
---

# Codex Usage Limits

## Purpose

Obtain the same values shown by Codex "Uso restante" without using an image. Codex stores rate-limit events locally as `codex.rate_limits` events in SQLite logs and newer session JSONL files. When the user explicitly asks about free/banked Codex resets, use the optional reset-credits flow below.

## Scope

Use this for Codex App and Codex terminal/CLI when they write local logs under the same Codex home directory. The Python script is cross-platform and defaults to `CODEX_HOME` or `~/.codex`.

This method depends on local log availability, not on the UI. If Codex terminal uses a different `CODEX_HOME`, pass it with `--codex-home`. The script reads both `logs_2.sqlite` websocket events and newer `sessions/**/*.jsonl` `rate_limits` entries, then uses the newest valid event.

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

Check banked/free Codex reset credits and expiry dates:

```powershell
& "$env:USERPROFILE\.codex\skills\codex-usage-limits\scripts\codex_usage_limits.ps1" -ResetCredits
```

```bash
python3 ~/.codex/skills/codex-usage-limits/scripts/codex_usage_limits.py --reset-credits
```

## Manual Steps

1. Locate the active Codex logs database. Prefer the newest existing file among:
   - `%USERPROFILE%\.codex\sqlite\logs_2.sqlite`
   - `%USERPROFILE%\.codex\logs_2.sqlite`
   - `$HOME/.codex/sqlite/logs_2.sqlite`
   - `$HOME/.codex/logs_2.sqlite`
2. Open it read-only with SQLite.
3. Query recent SQLite log rows containing `websocket event:` or `Received message`.
4. Parse the JSON payload after the marker with `json.JSONDecoder().raw_decode(...)`; rows can contain suffix text.
5. Also scan recent `sessions/**/*.jsonl` rows containing top-level `rate_limits` or `payload.rate_limits`.
6. Select the newest valid Codex limit event by timestamp.
7. Read:
   - `rate_limits.primary`: 5-hour window.
   - `rate_limits.secondary`: weekly window.
8. Convert the stored used percentage to UI remaining percentage:
   - `remaining_percent = 100 - used_percent`
9. Convert `reset_at`/`resets_at` from Unix seconds to local time. That is when the window renews.

## Field Meaning

- `primary.window_minutes == 300`: 5-hour limit.
- `secondary.window_minutes == 10080`: weekly limit.
- `used_percent`: percentage already consumed.
- `api_used_percent`: same API value, exposed explicitly.
- UI "Uso restante": `100 - used_percent`.
- `ui_remaining_percent`: exact value to compare with the UI percentage.
- `*_percent_exact`: string representation that preserves decimals if the API emits them.
- `reset_after_seconds`: seconds until renewal from the event timestamp.
- `reset_at`: absolute renewal timestamp.
- `event_age_seconds`: age of the local `codex.rate_limits` event. If it is too old, trigger a new Codex model response and rerun.

## Banked Reset Credits

Use this only when the user asks about free, available, banked, courtesy, or referral Codex resets and their expiry dates. This is separate from local `codex.rate_limits`.

The script reads `$CODEX_HOME/auth.json` or `~/.codex/auth.json`, sends the access token to ChatGPT's internal endpoint, and prints a sanitized result:

```text
https://chatgpt.com/backend-api/wham/rate-limit-reset-credits
```

Expected useful fields are:

- `available_count`: number of available reset credits.
- `credits[].status`: usually `available` for usable credits.
- `credits[].reset_type`: reset category, for example `codex_rate_limits`.
- `credits[].granted_at` / `credits[].expires_at`: when the credit was granted and when it expires.

Do not print tokens, `auth.json`, raw authorization headers, or raw account IDs. Treat this endpoint as an undocumented internal workaround; if it fails or changes shape, state that no stable public API is available and fall back to the official UI/support guidance.

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
