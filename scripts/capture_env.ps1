# Capture the hardware/software environment for the report's Methodology section.
# Run from the repo root in PowerShell (ideally "Run as administrator" so SSD health/temperature is readable):
#   powershell -ExecutionPolicy Bypass -File scripts\capture_env.ps1 -DriveLetter D
param(
    [string]$DriveLetter = "",
    [string]$OutFile = "data\env\environment.txt"
)
New-Item -ItemType Directory -Force -Path (Split-Path $OutFile) | Out-Null

function Section($title, $script) {
    "`n===== $title =====" | Out-File $OutFile -Append -Encoding utf8
    try { & $script | Out-String | Out-File $OutFile -Append -Encoding utf8 }
    catch { "(failed: $_)" | Out-File $OutFile -Append -Encoding utf8 }
}

"Captured: $(Get-Date -Format s)" | Out-File $OutFile -Encoding utf8

Section "Computer"   { Get-CimInstance Win32_ComputerSystem | Format-List Manufacturer, Model, TotalPhysicalMemory }
Section "CPU"        { Get-CimInstance Win32_Processor | Format-List Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed }
Section "OS"         { Get-CimInstance Win32_OperatingSystem | Format-List Caption, Version, BuildNumber, OSArchitecture }
Section "Power plan" { powercfg /getactivescheme }
Section "Disk drives (model, firmware, interface)" { Get-CimInstance Win32_DiskDrive | Format-List Index, Model, FirmwareRevision, InterfaceType, Size, BytesPerSector }
Section "Physical disks (media/bus type, health)"   { Get-PhysicalDisk | Format-List DeviceId, FriendlyName, MediaType, BusType, Size, HealthStatus, OperationalStatus }
Section "Volumes (filesystem, free space)"          { Get-Volume | Where-Object DriveLetter | Format-Table DriveLetter, FileSystemLabel, FileSystem, Size, SizeRemaining -AutoSize }
Section "Drive letter -> disk number"               { Get-Partition | Where-Object DriveLetter | Format-Table DriveLetter, DiskNumber, PartitionNumber -AutoSize }
Section "SSD health counters (temperature, wear) - needs admin" {
    Get-PhysicalDisk | Get-StorageReliabilityCounter | Format-List DeviceId, Temperature, TemperatureMax, Wear, PowerOnHours, ReadErrorsTotal, WriteErrorsTotal
}
Section "Write cache policy (Device Manager > Disk > Policies; not scriptable reliably)" { "Check manually and note: 'Enable write caching on the device' on/off" }
Section "fio"        { fio --version }
Section "Python"     { python --version }

if ($DriveLetter -ne "") {
    Section "Test drive $DriveLetter" {
        $dn = (Get-Partition -DriveLetter $DriveLetter).DiskNumber
        "Drive $DriveLetter is on physical disk number $dn"
        Get-PhysicalDisk | Where-Object { $_.DeviceId -eq $dn } | Format-List FriendlyName, MediaType, BusType, Size
    }
}
Write-Host "Wrote $OutFile"
