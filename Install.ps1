param([switch]$Restore)
$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = $base
if (!(Test-Path (Join-Path $root 'gmod.exe'))) { $root = Split-Path -Parent $base }
function HashFile([string]$path) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $stream = [System.IO.File]::OpenRead($path)
    try { return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
    finally { $stream.Close(); $sha.Clear() }
}
try {
    if (!(Test-Path (Join-Path $root 'gmod.exe'))) {
        throw 'Put these patch files in the GarrysMod game folder, or in a subfolder directly below it, then run this script again.'
    }
    if (Get-Process -Name 'gmod','gmod_win64','hl2' -ErrorAction SilentlyContinue) { throw 'Close Garrys Mod before installing or restoring.' }
    $items = @(
        @{ Rel='bin\steam_api.dll'; Backup='bin\steam_api_original.dll'; Payload='payload32\steam_api.dll'; OriginalHash='fdafb7c65ec7d4182b42bf92cc8671c68e4dc547cc6e613899d2618a47eb65da'; PreviousHash='53f5244c5654af9dab64579eb8e92ac2759dc2d5c2f8fb8820239f968c2141e4'; PreviousHash2='798ceb26096612d3f9d0b4330e7428e6e6949c2c7486f6dd36c0c429d72f1771' },
        @{ Rel='bin\win64\steam_api64.dll'; Backup='bin\win64\steam_api64_original.dll'; Payload='payload64\steam_api64.dll'; OriginalHash='eb17909a76668cf9ae0b92a618a34a50f6c73d3a6787cb4dd8ce36a8b10bfb75'; PreviousHash='b56fd67b8e700178f0c99e6a9eca35ef9ecd77ed26761c183da48d14742eee4e'; PreviousHash2='58b685f1532b9b69ccdbe124ee2b19cfbce183ea46466fac2c99486617ff1421' }
    )
    foreach ($item in $items) {
        $item.Target = Join-Path $root $item.Rel
        $item.Saved = Join-Path $root $item.Backup
        $item.Source = Join-Path $base $item.Payload
        $item.PatchHash = HashFile $item.Source
        if (!(Test-Path $item.Target)) { throw ('Game DLL missing: '+$item.Target) }
        $current = HashFile $item.Target
        if ($current -ne $item.OriginalHash -and $current -ne $item.PatchHash -and $current -ne $item.PreviousHash -and $current -ne $item.PreviousHash2) { throw ('Unrecognized or updated game DLL. No files changed: '+$item.Target) }
        if (Test-Path $item.Saved) {
            if ((HashFile $item.Saved) -ne $item.OriginalHash) { throw ('Existing backup is not the expected original. No files changed: '+$item.Saved) }
        } elseif ($Restore -or $current -ne $item.OriginalHash) { throw ('Original backup missing: '+$item.Saved) }
    }
    if ($Restore) {
        foreach ($item in $items) {
            [IO.File]::Copy($item.Saved,$item.Target,$true)
            if ((HashFile $item.Target) -ne $item.OriginalHash) { throw 'Restore verification failed.' }
            Write-Host ('Restored: '+$item.Rel)
        }
        Write-Host 'Original game Steam API libraries restored. Backups retained.'
    } else {
        foreach ($item in $items) {
            if (!(Test-Path $item.Saved)) { [IO.File]::Copy($item.Target,$item.Saved,$false) }
        }
        try {
            foreach ($item in $items) {
                [IO.File]::Copy($item.Source,$item.Target,$true)
                if ((HashFile $item.Target) -ne $item.PatchHash) { throw 'Install verification failed.' }
                Write-Host ('Installed: '+$item.Rel)
            }
        } catch {
            foreach ($item in $items) { [IO.File]::Copy($item.Saved,$item.Target,$true) }
            throw
        }
        Write-Host 'TEST3 installed for both 32-bit and 64-bit. Keep Steam running and launch Garrys Mod normally.'
        Write-Host ('Diagnostic log: '+(Join-Path $root 'GMod-LegacySteam.log'))
    }
} catch { Write-Host ('ERROR: '+$_.Exception.Message) -ForegroundColor Red; exit 1 }
