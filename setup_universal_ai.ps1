param([string]$UserEmail = ($env:USERNAME + "@local"))
$folder = $UserEmail + "_Universal_AI_v1.0"
$laws = Get-Content "C:\ailaws.md" -Raw -Encoding utf8
Set-Content "C:\ailaws.md" $laws -Encoding utf8
Set-Content "C:\00_ailaws.md" $laws -Encoding utf8
Set-Content "C:\GEMINI.md" $laws -Encoding utf8

$targets = @
("C:\" + $folder, $env:USERPROFILE + "\" + $folder, $env:USERPROFILE + "\.gemini\antigravity-cli\ai_space\" + $folder)
foreach ($d in $targets) {
    New-Item -ItemType Directory -Force -Path ($d + "\" + $UserEmail + "_keys"), ($d + "\payment_info"), ($d + "\cloud_storage"), ($d + "\summaries") | Out-Null
    Set-Content ($d + "\.gitignore") "*_keys/`r\npayment_info/`r\n*.key`r\n*.env`r\n*.secret`r\n!00_*.md" -Encoding utf8
    Set-Content ($d + "\user_nodes.csv") ( Label,Who,What,Where,Why,How,Full Name,Relationship,Phone,Email,Other Ways to Contact,Social Media Accounts,Home Address,Purpose,Task,Age,DOB,Alive or Dead,Date of Death,Notes,Timestamps of Edits`r\n`"" + $UserEmail + "`",`"Primary User`",`bActive User Profile`b,`bRoot System`",`"Primary Operator`",`"Autonomous Agent`",`"" + $UserEmail + "`",`bSelf`",`b`",`"" + $UserEmail + "`",```",`b`",``",`bSystem Tasks`",`"Node Management`",```",`b`",`"Alive`b,`b`",`"Initialized via Bootstrapper`",`"" + (Get-Date).ToString() + "`"" ) -Encoding utf8
}
Write-Host "[Success] Prompt any AI: read C:\ailaws.md and execute" -Foreground Green
