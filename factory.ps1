# Define the new paths to add
$newPaths = "%SystemRoot%\system32;%SystemRoot%;%SystemRoot%\System32\Wbem;%SYSTEMROOT%\System32\WindowsPowerShell\v1.0\;C:\Program Files (x86)\Windows Live\Shared"

# Get the current Path variable
$currentPath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")

# Combine the new paths with the current paths, avoiding duplicates
$updatedPath = $currentPath + ";" + $newPaths -split ';' | Sort-Object -Unique -join ';'

# Set the updated Path variable for the machine
[System.Environment]::SetEnvironmentVariable("Path", $updatedPath, "Machine")

# Output the updated Path variable for confirmation
Write-Output "Updated Path: $([System.Environment]::GetEnvironmentVariable("Path", "Machine"))"
