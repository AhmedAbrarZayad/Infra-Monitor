[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$RemoveData,
    [switch]$RemoveVirtualBox
)

$ErrorActionPreference = 'Stop'

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this script from an Administrator PowerShell window.'
}

$multipassExe = 'C:\Program Files\Multipass\bin\multipass.exe'
if (Test-Path -LiteralPath $multipassExe) {
    $instances = & $multipassExe list --format csv 2>$null
    if ($instances -match '(?m)^monitored-1,') {
        if ($PSCmdlet.ShouldProcess('Multipass instance monitored-1', 'Stop and permanently delete')) {
            & $multipassExe stop --force monitored-1 2>$null
            & $multipassExe delete --purge monitored-1
        }
    }
}

if (Get-Command winget.exe -ErrorAction SilentlyContinue) {
    if ($PSCmdlet.ShouldProcess('Canonical Multipass', 'Uninstall')) {
        & winget.exe uninstall --id Canonical.Multipass --exact --accept-source-agreements
    }

    if ($RemoveVirtualBox -and $PSCmdlet.ShouldProcess('Oracle VirtualBox', 'Uninstall')) {
        & winget.exe uninstall --id Oracle.VirtualBox --exact --accept-source-agreements
    }
} else {
    Write-Warning 'winget was not found. Uninstall Multipass from Settings > Apps > Installed apps.'
}

if ($RemoveData) {
    $allowedTargets = @(
        'C:\ProgramData\Multipass',
        'C:\Program Files\Multipass'
    )

    foreach ($target in $allowedTargets) {
        if (-not (Test-Path -LiteralPath $target)) {
            continue
        }

        $resolved = (Resolve-Path -LiteralPath $target).Path.TrimEnd('\')
        $expected = $target.TrimEnd('\')
        if (-not $resolved.Equals($expected, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to remove unexpected path: $resolved"
        }

        if ($PSCmdlet.ShouldProcess($resolved, 'Permanently remove Multipass leftover data')) {
            Remove-Item -LiteralPath $resolved -Recurse -Force
        }
    }
}

Write-Host 'Multipass cleanup finished.'
if (-not $RemoveVirtualBox) {
    Write-Host 'VirtualBox was left installed. Use -RemoveVirtualBox only if it was installed solely for this lab.'
}
