# Initialize counters
$totalDisconnected = 0
$totalMemoryFreed = 0

# Get the list of user sessions
$sessions = query user

# Skip the first line which is the header
$sessions = $sessions[1..($sessions.Length - 1)]

# Parse the session information
foreach ($session in $sessions) {
    $sessionDetails = $session -split '\s+'
    $username = $sessionDetails[0]
    $sessionId = $sessionDetails[2]
    $state = $sessionDetails[3]
    
    # Check if the user is disconnected
    if ($state -eq 'Disc') {
        Write-Host "Signing off session $sessionId for user $username"
        
        # Log off the user
        logoff $sessionId
        
        # Increment the disconnected counter
        $totalDisconnected++

        # Estimate memory freed (example: assuming each disconnected session frees up 100 MB)
        $memoryFreedPerSession = 100
        $totalMemoryFreed += $memoryFreedPerSession
    }
}

# Output the results
Write-Host "Total number of disconnected users: $totalDisconnected"
Write-Host "Total memory space freed up: $totalMemoryFreed MB"


#How to Run the Script
#powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\temp\disconnect-users.ps1


#Explanation of the Command:
#powershell.exe → Runs the PowerShell interpreter.
#-NoProfile → Runs PowerShell without loading user profiles for a faster startup.
#-ExecutionPolicy Bypass → Bypasses PowerShell's execution policy to allow the script to run.
#-File C:\temp\disconnect-users.ps1 → Specifies the script file to execute.


