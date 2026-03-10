# Installation

## One-Line Install

The fastest way to get started. This auto-installs all dependencies, clones the repo, and sets up your environment.

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/MhankBarBar/zero-ichi/master/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/MhankBarBar/zero-ichi/master/install.ps1 | iex
```

::: tip Custom Install Directory
Set `INSTALL_DIR` to change the install location (defaults to `~/zero-ichi`):
```bash
INSTALL_DIR=/opt/zero-ichi curl -fsSL https://raw.githubusercontent.com/MhankBarBar/zero-ichi/master/install.sh | bash
```
:::

---

## Requirements

- **Python 3.11+**
- **[uv](https://github.com/astral-sh/uv)** — fast Python package manager
- **FFmpeg** — required for audio/video processing
- **[Bun](https://bun.sh)** — required for YouTube JS challenge solving (yt-dlp)
- **Node.js 20+** — for the web dashboard (optional)

## Manual Install

```bash
# Install uv (if not already installed)
pip install uv

# Clone the repository
git clone https://github.com/MhankBarBar/zero-ichi
cd zero-ichi

# Install dependencies
uv sync
```

## Environment Setup

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```bash
AI_API_KEY=your_api_key_here
```

::: tip
The AI API key is only required if you plan to use the [Agentic AI](/features/ai) feature.
:::

## Next Steps

- [Configure the bot →](/getting-started/configuration)
- [Run the bot for the first time →](/getting-started/first-run)
