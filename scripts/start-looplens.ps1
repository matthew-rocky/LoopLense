param(
    [switch]$Check,
    [switch]$NoOpen,
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $ScriptDir "..")).Path
$FrontendDir = Join-Path $Root "frontend"
$VenvDir = Join-Path $Root ".venv"
$VenvPy = Join-Path $VenvDir "Scripts\python.exe"
$Requirements = Join-Path $Root "requirements.txt"
$FrontendPackage = Join-Path $FrontendDir "package.json"
$FrontendLock = Join-Path $FrontendDir "package-lock.json"
$NextBin = Join-Path $FrontendDir "node_modules\.bin\next.cmd"
$ApiUrl = "http://127.0.0.1:8000"
$ApiBase = "$ApiUrl/api"
$BackendHealth = "$ApiBase/health"
$FrontendUrl = "http://localhost:3000"

function Stop-WithMessage {
    param([string]$Message)
    Write-Host ""
    Write-Host $Message -ForegroundColor Red
    if (-not $NoPause) {
        Write-Host ""
        Read-Host "Press Enter to close" | Out-Null
    }
    exit 1
}

function Invoke-Step {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [string]$ErrorMessage
    )

    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -NoNewWindow -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        Stop-WithMessage $ErrorMessage
    }
}

function Test-Url {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400)
    } catch {
        return $false
    }
}

function Test-Port {
    param([int]$Port)
    $client = $null
    try {
        $client = [Net.Sockets.TcpClient]::new()
        $connect = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $connect.AsyncWaitHandle.WaitOne(500)) {
            return $false
        }
        $client.EndConnect($connect)
        return $true
    } catch {
        return $false
    } finally {
        if ($client) {
            $client.Close()
        }
    }
}

function Text-Contains {
    param(
        [string]$Text,
        [string]$Needle
    )
    if (-not $Text) {
        return $false
    }
    return $Text.IndexOf($Needle, [StringComparison]::OrdinalIgnoreCase) -ge 0
}

function Get-PortProcesses {
    param([int]$Port)
    try {
        $owners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($owner in $owners) {
            Get-CimInstance Win32_Process -Filter "ProcessId=$owner" -ErrorAction SilentlyContinue
        }
    } catch {
        @()
    }
}

function Stop-LoopLensPortProcess {
    param(
        [int]$Port,
        [string]$Kind
    )

    $processes = @(Get-PortProcesses $Port)
    if ($processes.Count -eq 0) {
        return $false
    }

    foreach ($process in $processes) {
        $commandLine = [string]$process.CommandLine
        $isFrontend = $Kind -eq "frontend" -and (Text-Contains $commandLine $FrontendDir) -and (Text-Contains $commandLine "next")
        $isBackend = $Kind -eq "backend" -and (Text-Contains $commandLine $Root) -and ((Text-Contains $commandLine "uvicorn") -or (Text-Contains $commandLine "backend.main:app"))

        if (-not ($isFrontend -or $isBackend)) {
            return $false
        }
    }

    foreach ($process in $processes) {
        Write-Host "Stopping stale LoopLens $Kind process on port $Port (PID $($process.ProcessId))..."
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    }

    for ($i = 1; $i -le 20; $i++) {
        if (-not (Test-Port $Port)) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }

    return (-not (Test-Port $Port))
}

function Clear-FrontendCache {
    $nextDir = Join-Path $FrontendDir ".next"
    if (-not (Test-Path $nextDir)) {
        return
    }

    $resolved = (Resolve-Path $nextDir).Path
    if (-not (Text-Contains $resolved $FrontendDir)) {
        Stop-WithMessage "Refusing to remove unexpected Next.js cache path: $resolved"
    }

    Write-Host "Clearing generated frontend cache..."
    Remove-Item -LiteralPath $resolved -Recurse -Force -ErrorAction SilentlyContinue
}

function Wait-ForUrl {
    param(
        [string]$Url,
        [string]$Name,
        [int]$Seconds
    )

    Write-Host "Waiting for $Name..."
    for ($i = 1; $i -le $Seconds; $i++) {
        if (Test-Url $Url) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

Write-Host "LoopLens local launcher" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend:  $ApiUrl"
Write-Host "Frontend: $FrontendUrl"
if ($Check) {
    Write-Host "Mode:     validation only"
}
if ($NoOpen) {
    Write-Host "Browser:  do not open automatically"
}
Write-Host ""

if (-not (Test-Path (Join-Path $Root "backend\main.py"))) {
    Stop-WithMessage "backend\main.py was not found. Keep RUN.bat in the LoopLens project root."
}

if (-not (Test-Path $FrontendPackage)) {
    Stop-WithMessage "frontend\package.json was not found. Keep RUN.bat in the LoopLens project root."
}

$python = Get-Command python -ErrorAction SilentlyContinue
$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $python -and -not $py) {
    Stop-WithMessage "Python was not found. Install Python 3, then run RUN.bat again."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Stop-WithMessage "npm was not found. Install Node.js LTS, then run RUN.bat again."
}

if (-not (Test-Path $VenvPy)) {
    Write-Host "Creating local Python virtual environment..."
    if ($python) {
        Invoke-Step $python.Source @("-m", "venv", $VenvDir) $Root "Python virtual environment creation failed."
    } else {
        Invoke-Step $py.Source @("-3", "-m", "venv", $VenvDir) $Root "Python virtual environment creation failed."
    }
}

& $VenvPy -c "import fastapi, uvicorn, pandas, polars, duckdb, pyarrow, httpx" *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing Python dependencies..."
    Invoke-Step $VenvPy @("-m", "pip", "install", "-r", $Requirements) $Root "Python dependency installation failed."
}

if (-not (Test-Path $NextBin)) {
    Write-Host "Installing frontend dependencies..."
    if (Test-Path $FrontendLock) {
        Invoke-Step "npm.cmd" @("ci") $FrontendDir "Frontend dependency installation failed."
    } else {
        Invoke-Step "npm.cmd" @("install") $FrontendDir "Frontend dependency installation failed."
    }
}

if ($Check) {
    Write-Host "Validation passed. Dependencies and project files look ready." -ForegroundColor Green
    exit 0
}

if (Test-Url $BackendHealth) {
    Write-Host "Backend is already running."
} else {
    if (Test-Port 8000) {
        if (-not (Stop-LoopLensPortProcess 8000 "backend")) {
            Stop-WithMessage "Port 8000 is already in use, but LoopLens backend health did not respond. Stop that process and run RUN.bat again."
        }
    }

    Write-Host "Starting backend..."
    $backendCommand = "title LoopLens Backend && `"$VenvPy`" -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/k", $backendCommand) -WorkingDirectory $Root | Out-Null

    if (-not (Wait-ForUrl $BackendHealth "backend" 45)) {
        Stop-WithMessage "Backend did not become ready at $BackendHealth."
    }
}

if (Test-Url $FrontendUrl) {
    Write-Host "Frontend is already running."
} else {
    if (Test-Port 3000) {
        if (-not (Stop-LoopLensPortProcess 3000 "frontend")) {
            Stop-WithMessage "Port 3000 is already in use, but the frontend did not respond at $FrontendUrl. Stop that process and run RUN.bat again."
        }
        Clear-FrontendCache
    } else {
        Clear-FrontendCache
    }

    Write-Host "Starting frontend..."
    $frontendCommand = "title LoopLens Frontend && set `"NEXT_PUBLIC_API_BASE_URL=$ApiBase`" && npm run dev"
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/k", $frontendCommand) -WorkingDirectory $FrontendDir | Out-Null

    if (-not (Wait-ForUrl $FrontendUrl "frontend" 75)) {
        Stop-WithMessage "Frontend did not become ready at $FrontendUrl."
    }
}

Write-Host ""
Write-Host "LoopLens is ready." -ForegroundColor Green
Write-Host $FrontendUrl

if (-not $NoOpen) {
    Start-Process $FrontendUrl
}

exit 0
