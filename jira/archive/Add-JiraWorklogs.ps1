<#
    Add-JiraWorklogs.ps1
    Writes the 43 reconstructed AFDS worklogs for 2026-08-23 .. 2026-09-19.

    Auth: needs an Atlassian API token (NOT your password).
      Create one at https://id.atlassian.com/manage-profile/security/api-tokens
      Then either set $env:JIRA_TOKEN before running, or let the script prompt.

    Usage:
      powershell -ExecutionPolicy Bypass -File .\Add-JiraWorklogs.ps1
      powershell -ExecutionPolicy Bypass -File .\Add-JiraWorklogs.ps1 -WhatIf
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Site  = "https://biplan-consulting.atlassian.net",
    [string]$Email = "sankerbaril@biplan.ca",
    [string]$Offset = "-0400"   # America/New_York, EDT in Aug/Sep 2026
)

# --- credentials -----------------------------------------------------------
$token = $env:JIRA_TOKEN
if ([string]::IsNullOrWhiteSpace($token)) {
    $secure = Read-Host "Atlassian API token" -AsSecureString
    $bstr   = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    $token  = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}
$pair    = "{0}:{1}" -f $Email, $token
$basic   = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($pair))
$headers = @{ Authorization = "Basic $basic"; Accept = "application/json" }

# --- the worklogs ----------------------------------------------------------
# date, issue key, seconds, comment
$rows = @(
    @("2026-08-24","AFDS-76" ,22500,"maintenance frm10-12 et power query"),
    @("2026-08-25","AFDS-76" ,22500,"maintenance frm10-12 et power query"),
    @("2026-08-26","AFDS-76" ,22500,"maintenance frm10-12 et power query"),
    @("2026-08-27","AFDS-62" ,20700,"analyse de la perte de donné et outil de récupération"),
    @("2026-08-27","AFDS-183",16200,"début du viewer sharepoint en lecture seule"),
    @("2026-08-28","AFDS-62" , 7200,"application de la récupération d'archive"),
    @("2026-08-28","AFDS-76" ,22500,"réparation du fichier frm10-12 corrompu"),
    @("2026-08-29","AFDS-76" , 9900,"remise en ordre des colonnes après réparation"),

    @("2026-08-30","AFDS-76" ,  900,"validation des règles de mise en forme conditionnelle"),
    @("2026-08-31","AFDS-76" ,18000,"problème d'accès au fichier et listes déroulantes manquantes"),
    @("2026-08-31","AFDS-207",17100,"correction de la connexion power bi et conception de la réconciliation"),
    @("2026-09-01","AFDS-206",21600,"coercition des types et des dates, réconciliation des prix"),
    @("2026-09-01","AFDS-183", 9900,"mappage des colonnes du viewer et rafraîchissement de l'archive"),
    @("2026-09-03","AFDS-207",12600,"planification des workstreams et outillage"),
    @("2026-09-04","AFDS-206",28800,"coercition ciblée à l'étape 8 et synchro du viewer"),
    @("2026-09-04","AFDS-76" , 5400,"suivi des preuves de récupération et snapshots"),
    @("2026-09-05","AFDS-150",29700,"scripts de migration et vérification"),

    @("2026-09-06","AFDS-150", 1800,"préparation de la migration"),
    @("2026-09-07","AFDS-150",24300,"préparation du cutover: flows et scripts de backfill"),
    @("2026-09-08","AFDS-207",22500,"flows de synchro parent et comparaison des listes"),
    @("2026-09-09","AFDS-183",19800,"corrections du viewer et contournement excel online"),
    @("2026-09-10","AFDS-150",33300,"journée de cutover: déploiement et tests des flows n3"),
    @("2026-09-11","AFDS-133", 9000,"déplacement vers le site client (granby)"),
    @("2026-09-11","AFDS-176",10800,"accompagnement des utilisateurs sur sharepoint"),
    @("2026-09-11","AFDS-212", 3600,"demandes de changement client (flow de nettoyage, bo report)"),
    @("2026-09-11","AFDS-183", 9900,"viewer déployé, marqueurs ec rendus"),
    @("2026-09-11","AFDS-133", 9000,"retour du site client"),

    @("2026-09-14","AFDS-133", 3600,"déplacement vers le site client (granby)"),
    @("2026-09-14","AFDS-212",10800,"déploiement du flow déclencheur v004"),
    @("2026-09-14","AFDS-92" ,10800,"conception du contrôle documentaire (dossiers bleus)"),
    @("2026-09-14","AFDS-176",10800,"accompagnement des utilisateurs sur sharepoint"),
    @("2026-09-14","AFDS-133", 3600,"retour du site client"),
    @("2026-09-15","AFDS-133", 3600,"déplacement vers le site client (granby)"),
    @("2026-09-15","AFDS-176",18000,"accompagnement des utilisateurs sur sharepoint"),
    @("2026-09-15","AFDS-212",14400,"ajustements des listes sharepoint et des flows"),
    @("2026-09-15","AFDS-133", 3600,"retour du site client"),
    @("2026-09-16","AFDS-133", 3600,"déplacement vers le site client (granby)"),
    @("2026-09-16","AFDS-212",12600,"conception et construction de l'archivage"),
    @("2026-09-16","AFDS-213", 5400,"test de la connexion monday.com"),
    @("2026-09-16","AFDS-176",10800,"accompagnement des utilisateurs sur sharepoint"),
    @("2026-09-16","AFDS-133", 9000,"retour du site client"),
    @("2026-09-17","AFDS-212",11700,"maintenance des listes sharepoint et des flows"),
    @("2026-09-18","AFDS-212",11700,"maintenance des listes sharepoint et des flows")
)

# --- sanity check: every week must land on exactly 40h ---------------------
$weekStart = [datetime]"2026-08-23"
$byWeek = @{}
foreach ($r in $rows) {
    $w = [math]::Floor(([datetime]$r[0] - $weekStart).TotalDays / 7) + 1
    $byWeek[$w] = [int]$byWeek[$w] + [int]$r[2]
}
Write-Host "Entries: $($rows.Count)" -ForegroundColor Cyan
foreach ($w in ($byWeek.Keys | Sort-Object)) {
    $h = [math]::Round($byWeek[$w] / 3600, 2)
    $flag = if ($h -eq 40) { "OK" } else { "CHECK" }
    Write-Host ("  Week {0}: {1}h  [{2}]" -f $w, $h, $flag)
}

# --- write -----------------------------------------------------------------
$cursor = @{}
$ok = 0
$failed = @()

foreach ($r in $rows) {
    $date = $r[0]; $key = $r[1]; $secs = [int]$r[2]; $comment = $r[3]

    # stagger start times within a day so entries read in order
    $offsetSecs = [int]$cursor[$date]
    $cursor[$date] = $offsetSecs + $secs
    $h = 8 + [int][math]::Floor($offsetSecs / 3600)
    $m = [int][math]::Floor(($offsetSecs % 3600) / 60)
    $started = "{0}T{1:d2}:{2:d2}:00.000{3}" -f $date, $h, $m, $Offset

    $payload = @{
        started          = $started
        timeSpentSeconds = $secs
        comment          = @{
            type    = "doc"
            version = 1
            content = @(@{ type = "paragraph"; content = @(@{ type = "text"; text = $comment }) })
        }
    }

    $label = "{0}  {1,-9} {2,5}s  {3}" -f $date, $key, $secs, $comment
    if (-not $PSCmdlet.ShouldProcess($label, "Create worklog")) { continue }

    $uri  = "$Site/rest/api/3/issue/$key/worklog?notifyUsers=false"
    $json = $payload | ConvertTo-Json -Depth 10 -Compress
    $body = [Text.Encoding]::UTF8.GetBytes($json)

    try {
        $null = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $body -ContentType "application/json"
        $ok++
        Write-Host "  + $label" -ForegroundColor Green
    } catch {
        $failed += "$label  ->  $($_.Exception.Message)"
        Write-Host "  ! $label" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Created: $ok / $($rows.Count)" -ForegroundColor Cyan
if ($failed.Count) {
    Write-Host "Failed:" -ForegroundColor Red
    $failed | ForEach-Object { Write-Host "  $_" }
}
