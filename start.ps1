try {
    Write-Host "Starting LLM Council..."
    Write-Host ""

    # Determine backend command
    if (Get-Command "uv" -ErrorAction SilentlyContinue) {
        $backendExe = "uv"
        $backendArgs = "run python -m backend.main"
        Write-Host "Using 'uv' to start backend..."
    } elseif (Get-Command "python" -ErrorAction SilentlyContinue) {
        $backendExe = "python"
        $backendArgs = "-m backend.main"
        Write-Host "Using 'python' to start backend..."
    } else {
        Write-Error "Error: Neither 'uv' nor 'python' found in PATH. Please ensure Python is installed and added to PATH, or activate your virtual environment."
        exit 1
    }

    # Determine frontend command
    if (Get-Command "npm.cmd" -ErrorAction SilentlyContinue) {
        $frontendExe = "npm.cmd"
    } else {
        $frontendExe = "npm"
    }

    # Start backend
    Write-Host "Starting backend on http://localhost:8001..."
    $backendProcess = Start-Process -FilePath $backendExe -ArgumentList $backendArgs -PassThru -NoNewWindow -ErrorAction Stop
    Write-Host "Backend started (PID: $($backendProcess.Id))"

    # Wait a bit for backend to start
    Start-Sleep -Seconds 2

    # Start frontend
    Write-Host "Starting frontend on http://localhost:5173..."
    Push-Location frontend

    try {
        $frontendProcess = Start-Process -FilePath $frontendExe -ArgumentList "run dev -- --host" -PassThru -NoNewWindow -ErrorAction Stop
        Write-Host "Frontend started (PID: $($frontendProcess.Id))"
    } catch {
        Write-Error "Failed to start frontend. Ensure 'npm' is installed and in PATH."
        throw $_
    } finally {
        Pop-Location
    }

    Write-Host ""
    Write-Host "LLM Council is running!"
    Write-Host "  Backend:  http://localhost:8001"
    Write-Host "  Frontend: http://localhost:5173"
    Write-Host ""
    Write-Host "Press Ctrl+C to stop both servers"

    # Wait for the processes to exit or user interruption
    while ($true) {
        if ($backendProcess.HasExited) {
            Write-Error "Backend process exited unexpectedly. Exit Code: $($backendProcess.ExitCode)"
            break
        }
        if ($frontendProcess.HasExited) {
            Write-Error "Frontend process exited unexpectedly. Exit Code: $($frontendProcess.ExitCode)"
            break
        }
        Start-Sleep -Milliseconds 500
    }
}
finally {
    Write-Host "`nStopping servers..."

    # Function to stop a process and its children
    function Stop-ProcessTree {
        param(
            [Parameter(Mandatory=$true)]
            [int]$ProcessId,

            [Parameter(Mandatory=$false)]
            [string]$ProcessName
        )

        if ($ProcessId -gt 0) {
            try {
                $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
                if ($process) {
                    $process | Stop-Process -Force -ErrorAction SilentlyContinue
                    Write-Host "  Stopped $ProcessName (PID: $ProcessId)"
                }
            } catch {
                Write-Host "  Could not stop $ProcessName (PID: $ProcessId): $_"
            }
        }

        # Also try to stop any child processes (npm/node processes)
        try {
            Get-Process -ErrorAction SilentlyContinue | Where-Object {
                $_.Parent.Id -eq $ProcessId -or
                ($ProcessName -match 'npm|node' -and $_.ProcessName -match 'npm|node')
            } | ForEach-Object {
                try {
                    $_ | Stop-Process -Force -ErrorAction SilentlyContinue
                    Write-Host "  Stopped child process ($($_.ProcessName), PID: $($_.Id))"
                } catch {
                    # Ignore errors when stopping children
                }
            }
        } catch {
            # Ignore errors when finding child processes
        }
    }

    if ($null -ne $backendProcess -and $backendProcess.Id -gt 0) {
        Stop-ProcessTree -ProcessId $backendProcess.Id -ProcessName "Backend"
    }
    if ($null -ne $frontendProcess -and $frontendProcess.Id -gt 0) {
        Stop-ProcessTree -ProcessId $frontendProcess.Id -ProcessName "Frontend"
    }
}
