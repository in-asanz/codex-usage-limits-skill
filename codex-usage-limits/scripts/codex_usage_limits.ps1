param(
    [string] $CodexHome,
    [string] $Db,
    [switch] $Json
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

python @ArgsList
