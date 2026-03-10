#Requires -Version 5.1

$ErrorActionPreference = "Stop"

function Write-Info  { Write-Host "[INFO]  " -ForegroundColor Cyan -NoNewline; Write-Host $args }
function Write-Ok    { Write-Host "[OK]    " -ForegroundColor Green -NoNewline; Write-Host $args }
function Write-Warn  { Write-Host "[WARN]  " -ForegroundColor Yellow -NoNewline; Write-Host $args }
function Write-Fail  { Write-Host "[FAIL]  " -ForegroundColor Red -NoNewline; Write-Host $args; exit 1 }

Write-Host ""
Write-Host "+==============================================+" -ForegroundColor White
Write-Host "|           Zero Ichi Installer                |" -ForegroundColor White
Write-Host "|         WhatsApp Bot built with <3            |" -ForegroundColor White
Write-Host "+==============================================+" -ForegroundColor White
Write-Host ""

$InstallDir = if ($env:INSTALL_DIR) { $env:INSTALL_DIR } else { Join-Path $HOME "zero-ichi" }
$RepoUrl = "https://github.com/MhankBarBar/zero-ichi.git"
$Branch = if ($env:BRANCH) { $env:BRANCH } else { "main" }

function Test-Command { param($Name) return [bool](Get-Command $Name -ErrorAction SilentlyContinue) }

function Update-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
}

function Test-Python {
    $pyCmd = $null
    foreach ($cmd in @("python", "python3")) {
        if (Test-Command $cmd) {
            $ver = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($ver) {
                $parts = $ver.Split(".")
                if ([int]$parts[0] -ge 3 -and [int]$parts[1] -ge 11) {
                    $pyCmd = $cmd
                    break
                }
            }
        }
    }
    if ($pyCmd) {
        Write-Ok "Python $ver found ($pyCmd)"
    } else {
        Write-Fail "Python 3.11+ is required. Download from https://python.org"
    }
}

function Test-Uv {
    if (Test-Command "uv") {
        Write-Ok "uv found ($(uv --version))"
    } else {
        Write-Info "Installing uv..."
        irm https://astral.sh/uv/install.ps1 | iex
        Update-Path
        if (Test-Command "uv") {
            Write-Ok "uv installed ($(uv --version))"
        } else {
            Write-Fail "Failed to install uv. Install manually: https://docs.astral.sh/uv/"
        }
    }
}

function Test-FFmpeg {
    if (Test-Command "ffmpeg") {
        Write-Ok "FFmpeg found"
    } else {
        if (Test-Command "winget") {
            Write-Info "Installing FFmpeg via winget..."
            winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements --silent
            Update-Path
            if (Test-Command "ffmpeg") {
                Write-Ok "FFmpeg installed"
            } else {
                Write-Warn "FFmpeg installed but not in PATH. Restart your terminal or add it to PATH manually."
            }
        } else {
            Write-Warn "FFmpeg not found. Install it from https://ffmpeg.org or via: winget install Gyan.FFmpeg"
        }
    }
}

function Test-Bun {
    if (Test-Command "bun") {
        Write-Ok "Bun found ($(bun --version))"
    } else {
        Write-Info "Installing Bun (needed for YouTube downloads)..."
        irm https://bun.sh/install.ps1 | iex
        Update-Path
        if (Test-Command "bun") {
            Write-Ok "Bun installed ($(bun --version))"
        } else {
            Write-Warn "Bun installation failed. YouTube downloads may not work."
        }
    }
}

function Test-Git {
    if (Test-Command "git") {
        Write-Ok "Git found"
    } else {
        Write-Fail "Git is required. Install from https://git-scm.com or: winget install Git.Git"
    }
}

Write-Info "Checking dependencies..."
Write-Host ""
Test-Git
Test-Python
Test-Uv
Test-FFmpeg
Test-Bun
Write-Host ""

if (Test-Path $InstallDir) {
    Write-Info "Directory $InstallDir already exists, pulling latest..."
    Push-Location $InstallDir
    try { git pull --ff-only origin $Branch } catch { Write-Warn "Git pull failed, continuing with existing code." }
} else {
    Write-Info "Cloning Zero Ichi to $InstallDir..."
    git clone --depth 1 --branch $Branch $RepoUrl $InstallDir
    Push-Location $InstallDir
}

Write-Info "Installing Python dependencies..."
uv sync --quiet
Write-Ok "Dependencies installed"

$envFile = Join-Path $InstallDir ".env"
$envExample = Join-Path $InstallDir ".env.example"
if (-not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
    Write-Ok "Created .env from .env.example"
    Write-Warn "Edit $envFile to configure your bot."
} else {
    Write-Ok ".env already exists, skipping."
}

Pop-Location

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  To start the bot:" -ForegroundColor White
Write-Host "    cd $InstallDir"
Write-Host "    uv run zero-ichi"
Write-Host ""
Write-Host "  First run:" -ForegroundColor White
Write-Host "    Scan the QR code with WhatsApp -> Settings -> Linked Devices"
Write-Host ""
Write-Host "  Docs: https://zeroichi.mhankbarbar.dev" -ForegroundColor White
Write-Host ""
