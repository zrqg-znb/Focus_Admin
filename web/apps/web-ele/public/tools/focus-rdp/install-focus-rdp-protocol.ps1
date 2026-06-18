# Focus RDP protocol installer
# Run once on Windows client machines. It registers focus-rdp:// for the current user
# and routes focus-rdp://open?host=<ip-or-hostname> to mstsc.exe /v:<host>.

$ErrorActionPreference = 'Stop'

$InstallDir = Join-Path $env:ProgramData 'FocusRdp'
$LauncherPath = Join-Path $InstallDir 'focus-rdp-launcher.ps1'

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

$LauncherScript = @'
param(
    [Parameter(Mandatory = $true)]
    [string]$LaunchUrl
)

$ErrorActionPreference = 'Stop'

try {
    $decodedUrl = [System.Uri]::UnescapeDataString($LaunchUrl)
    $hostValue = $null

    if ($decodedUrl -match '[?&]host=([^&]+)') {
        $hostValue = [System.Uri]::UnescapeDataString($Matches[1])
    } elseif ($decodedUrl -match '^focus-rdp://([^/?#]+)') {
        $hostValue = [System.Uri]::UnescapeDataString($Matches[1])
    }

    if ([string]::IsNullOrWhiteSpace($hostValue)) {
        throw 'Missing host parameter.'
    }

    $hostValue = $hostValue.Trim()
    if ($hostValue.Length -gt 253 -or $hostValue -notmatch '^[A-Za-z0-9.-]+$') {
        throw "Invalid host value: $hostValue"
    }

    $mstscPath = Join-Path $env:SystemRoot 'System32\mstsc.exe'
    if (-not (Test-Path $mstscPath)) {
        throw 'mstsc.exe was not found.'
    }

    Start-Process -FilePath $mstscPath -ArgumentList @("/v:$hostValue")
} catch {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        "Focus RDP failed to open Remote Desktop.`n$($_.Exception.Message)",
        'Focus RDP',
        'OK',
        'Error'
    ) | Out-Null
}
'@

Set-Content -Path $LauncherPath -Value $LauncherScript -Encoding UTF8

$ProtocolRoot = 'HKCU:\Software\Classes\focus-rdp'
$CommandKey = Join-Path $ProtocolRoot 'shell\open\command'

New-Item -Path $CommandKey -Force | Out-Null
Set-Item -Path $ProtocolRoot -Value 'URL:Focus RDP Protocol'
New-ItemProperty -Path $ProtocolRoot -Name 'URL Protocol' -Value '' -PropertyType String -Force | Out-Null

$Command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$LauncherPath`" `"%1`""
Set-Item -Path $CommandKey -Value $Command

Write-Host 'Focus RDP protocol installed successfully.'
Write-Host 'Test URL: focus-rdp://open?host=127.0.0.1'
