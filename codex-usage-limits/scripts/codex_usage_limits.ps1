param(
    [string] $CodexHome,
    [string] $Db,
    [switch] $Json,
    [switch] $Percentages,
    [int] $FailIfStaleSeconds
)

$ErrorActionPreference = "Stop"
$ScriptPath = Join-Path $PSScriptRoot "codex_usage_limits.py"
$ArgsList = @($ScriptPath)

if ($CodexHome) {
    $ArgsList += @("--codex-home", $CodexHome)
}

if ($Db) {
    $ArgsList += @("--db", $Db)
}

if ($Json) {
    $ArgsList += "--json"
}

if ($Percentages) {
    $ArgsList += "--percentages"
}

if ($FailIfStaleSeconds) {
    $ArgsList += @("--fail-if-stale-seconds", $FailIfStaleSeconds)
}

python @ArgsList
