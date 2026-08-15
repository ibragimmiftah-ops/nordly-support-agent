param(
    [Parameter(Mandatory)][string]$EncryptedBackup,
    [Parameter(Mandatory)][string]$AgeIdentityFile,
    [Parameter(Mandatory)][ValidateSet("RESTORE")][string]$ConfirmRestore
)
$ErrorActionPreference = "Stop"
if (-not $env:PGDATABASE) { throw "PGDATABASE is required" }
if ($env:PGPASSWORD_FILE) { $env:PGPASSWORD = (Get-Content -LiteralPath $env:PGPASSWORD_FILE -Raw).Trim() }
$temporaryDump = Join-Path ([IO.Path]::GetTempPath()) "nordly-$([guid]::NewGuid()).dump"
try {
    $checksumFile = "$EncryptedBackup.sha256"
    if (Test-Path -LiteralPath $checksumFile) {
        $expected = ((Get-Content -LiteralPath $checksumFile -Raw).Trim() -split "\s+")[0]
        $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $EncryptedBackup).Hash
        if ($actual -ne $expected) { throw "Backup checksum mismatch" }
    }
    & age --decrypt --identity $AgeIdentityFile --output $temporaryDump $EncryptedBackup
    if ($LASTEXITCODE -ne 0) { throw "age decryption failed" }
    & pg_restore --list $temporaryDump | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Archive verification failed" }
    & pg_restore --exit-on-error --clean --if-exists --no-owner --no-privileges --dbname=$env:PGDATABASE $temporaryDump
    if ($LASTEXITCODE -ne 0) { throw "PostgreSQL restore failed" }
    "PostgreSQL restore completed and archive structure verified: $env:PGDATABASE"
} finally {
    Remove-Item -LiteralPath $temporaryDump -Force -ErrorAction SilentlyContinue
}
