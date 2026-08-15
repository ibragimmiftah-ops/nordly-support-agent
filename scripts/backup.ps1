param(
    [Parameter(Mandatory)][string]$OutputDirectory,
    [Parameter(Mandatory)][string]$AgeRecipient,
    [int]$RetentionDays = 30
)
$ErrorActionPreference = "Stop"
if (-not (Get-Command pg_dump -ErrorAction SilentlyContinue)) { throw "pg_dump is required" }
if (-not (Get-Command pg_restore -ErrorAction SilentlyContinue)) { throw "pg_restore is required" }
if (-not (Get-Command age -ErrorAction SilentlyContinue)) { throw "age is required" }
if ($env:PGPASSWORD_FILE) { $env:PGPASSWORD = (Get-Content -LiteralPath $env:PGPASSWORD_FILE -Raw).Trim() }
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$temporaryDump = Join-Path ([IO.Path]::GetTempPath()) "nordly-$([guid]::NewGuid()).dump"
$outputFile = Join-Path $OutputDirectory "nordly-postgresql-$timestamp.dump.age"
try {
    & pg_dump --format=custom --no-owner --no-privileges --file=$temporaryDump
    if ($LASTEXITCODE -ne 0) { throw "pg_dump failed" }
    & pg_restore --list $temporaryDump | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "pg_dump archive verification failed" }
    & age --recipient $AgeRecipient --output $outputFile $temporaryDump
    if ($LASTEXITCODE -ne 0) { throw "age encryption failed" }
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $outputFile).Hash.ToLowerInvariant()
    "$hash  $([IO.Path]::GetFileName($outputFile))" | Set-Content -Encoding ascii "$outputFile.sha256"
    Get-ChildItem -LiteralPath $OutputDirectory -Filter "nordly-postgresql-*.dump.age*" |
        Where-Object LastWriteTimeUtc -lt (Get-Date).ToUniversalTime().AddDays(-$RetentionDays) |
        Remove-Item -Force
    "Encrypted PostgreSQL backup created and source dump verified: $outputFile"
} finally {
    Remove-Item -LiteralPath $temporaryDump -Force -ErrorAction SilentlyContinue
}
