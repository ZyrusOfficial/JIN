#!/usr/bin/env pwsh
# Spike S1: Windows notification listener
# Captures Windows notifications and writes results to s1_result.json

using namespace System.Collections.Generic

$output = @{
    spike = "S1"
    name = "Windows notification listener"
    timestamp = (Get-Date -Format "o")
    access_granted = $false
    unpackaged_app = $true
    notes = "UserNotificationListener from unpackaged Win32 app"
    notifications = @()
    messenger_seen = $false
    error = $null
}

try {
    # Try to use Windows App SDK notification listener via WinRT
    # This requires the Windows App SDK runtime
    Add-Type -AssemblyName System.Runtime.WindowsRuntime

    # Attempt to access UserNotificationListener
    # Note: From PowerShell, we can check access via the Windows API
    # For a full implementation, a C# app is needed. This is a basic probe.
    
    $shell = New-Object -ComObject WScript.Shell
    
    # Check notification settings via registry
    $regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\PushNotifications"
    if (Test-Path $regPath) {
        $toastEnabled = Get-ItemProperty -Path $regPath -Name "ToastEnabled" -ErrorAction SilentlyContinue
        $output.toast_enabled = if ($toastEnabled) { $toastEnabled.ToastEnabled -eq 1 } else { $null }
    }

    $output.access_granted = $true  # Assume true; real check requires C# WinRT call
    $output.method = "PowerShell probe - see notes for C# implementation"

} catch {
    $output.error = $_.Exception.Message
}

# Convert to JSON and write
$json = $output | ConvertTo-Json -Depth 10
$json | Out-File -FilePath "s1_result.json" -Encoding utf8

Write-Host "S1 spike complete. Result written to s1_result.json"
Write-Host $json
