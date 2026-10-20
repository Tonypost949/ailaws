<#
    setup_universal_ai.ps1  —  Universal AI Laws bootstrapper (idempotent, non-destructive)
    Canonical laws: C:\Amd949609_Antigravity_v1\00_ailaws.md
    Repo mirror  : https://github.com/Tonypost949/ailaws
    Installs the law file(s) + the user-folder skeleton. Never deletes user data:
    existing files are copied to a timestamped backup before being overwritten.
#>
param(
    [string]$UserEmail  = ($env:USERNAME + "@local"),
    [string]$SourceLaws = ""
)

$ErrorActionPreference = "Stop"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"

# ---- 1. locate the canonical laws file -------------------------------------
$candidates = @(
    $SourceLaws,
    "C:\Amd949609_Antigravity_v1\00_ailaws.md",
    "$PSScriptRoot\00_ailaws.md",
    "C:\00_ailaws.md"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

if (-not $candidates -or $candidates.Count -eq 0) {
    throw "No laws file found. Expected C:\Amd949609_Antigravity_v1\00_ailaws.md or 00_ailaws.md next to this script."
}
$lawsPath = $candidates[0]
$laws = Get-Content -LiteralPath $lawsPath -Raw -Encoding utf8

# ---- 2. tripwire: refuse to propagate a gutted laws file --------------------
foreach ($marker in @("SOURCE OF TRUTH RULE", "ERROR COIN", "YOLO Mode")) {
    if ($laws -notmatch [regex]::Escape($marker)) {
        throw "ABORT: canonical laws file '$lawsPath' is missing required content: '$marker'. Nothing was written."
    }
}

$backup = "C:\Amd949609_Antigravity_v1\backups\ailaws_$stamp"
New-Item -ItemType Directory -Force -Path $backup | Out-Null

function Set-LawFile([string]$Path) {
    if (Test-Path -LiteralPath $Path) {
        Copy-Item -LiteralPath $Path -Destination (Join-Path $backup (Split-Path $Path -Leaf)) -Force
    }
    $dir = Split-Path $Path -Parent
    if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    Set-Content -LiteralPath $Path -Value $laws -Encoding utf8 -NoNewline
    Write-Host "  laws -> $Path"
}

# ---- 3. law files ----------------------------------------------------------
Write-Host "Installing Universal AI Laws from $lawsPath"
Set-LawFile "C:\00_ailaws.md"
Set-LawFile "C:\AGENTS.md"
Set-LawFile "C:\ailaws.md"                 # legacy prompt path: "read C:\ailaws.md and execute"
Set-LawFile "C:\Amd949609_Antigravity_v1\AGENTS.md"

# ---- 4. user folder skeleton ----------------------------------------------
$folder   = "${UserEmail}_Universal_AI_v1.0"
$targets  = @(
    ("C:\" + $folder),
    ($env:USERPROFILE + "\" + $folder),
    ($env:USERPROFILE + "\.gemini\antigravity-cli\ai_space\" + $folder)
)
$subdirs  = @("${UserEmail}_keys", "payment_info", "cloud_storage", "summaries", "scripts", "mcp_configs", "skills", "plugins", "docs", "tasks", "evidence")
$gitignore = @(
    "*_keys/", "payment_info/", "*.key", "*.env", "*.secret", "*.pem", "*.pfx",
    "*credentials*", "*token*", "!00_*.md"
) -join "`r`n"

foreach ($d in $targets) {
    foreach ($s in $subdirs) { New-Item -ItemType Directory -Force -Path (Join-Path $d $s) | Out-Null }
    Set-Content -LiteralPath (Join-Path $d ".gitignore") -Value $gitignore -Encoding utf8
    Set-LawFile (Join-Path $d "00_ailaws.md")
    Set-LawFile (Join-Path $d "AGENTS.md")

    $nodes = Join-Path $d "user_nodes.csv"
    if (-not (Test-Path -LiteralPath $nodes)) {
        $rows = @(
            "Label,Who,What,Where,Why,How,Full Name,Relationship,Phone,Email,Other Ways to Contact,Social Media Accounts,Home Address,Purpose,Task,Age,DOB,Alive or Dead,Date of Death,Notes,Timestamps of Edits",
            ('"{0}","Primary User","Active User Profile","Root System","Primary Operator","Autonomous Agent","{0}","Self","","{0}","","","","System Tasks","Node Management","","","Alive","","Initialized via Bootstrapper","{1}"' -f $UserEmail, $stamp)
        )
        Set-Content -LiteralPath $nodes -Value $rows -Encoding utf8
    }
    Write-Host "  user folder -> $d"
}

Write-Host ""
Write-Host "[Success] Laws installed (backup: $backup)" -ForegroundColor Green
Write-Host "[Success] Prompt any AI: read C:\Amd949609_Antigravity_v1\00_ailaws.md and execute" -ForegroundColor Green
