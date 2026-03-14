---
layout: home

hero:
  name: Zero Ichi
  text: WhatsApp Bot
  tagline: "A powerful WhatsApp bot built with Python + Neonize — packed with AI, media downloader, group management, and a web dashboard."
  image:
    src: /logo.png
    alt: Zero Ichi Logo
  actions:
    - theme: brand
      text: Get Started
      link: /getting-started/installation
    - theme: alt
      text: View on GitHub
      link: https://github.com/MhankBarBar/zero-ichi

features:
  - icon:
      src: /icons/bot.svg
    title: Agentic AI
    details: "Built-in AI assistant that understands context, remembers conversations, and can execute bot commands on your behalf. Bring your own API key."
    link: /features/ai
    linkText: Learn more
  - icon:
      src: /icons/download.svg
    title: Media Downloader
    details: "Download audio & video from YouTube, TikTok, Instagram, Twitter/X, and 1000+ sites — powered by yt-dlp with quality selection."
    link: /commands/downloader
    linkText: See commands
  - icon:
      src: /icons/shield.svg
    title: Group Management
    details: "Moderation toolkit with anti-link, anti-delete, blacklist, warnings, welcome/goodbye messages, polls, and role-based permissions."
    link: /commands/group
    linkText: See commands
  - icon:
      src: /icons/globe.svg
    title: Multi-Language (i18n)
    details: "Full internationalization with English + Indonesian built in. Easily add new languages with JSON locale files — no code changes needed."
    link: /features/i18n
    linkText: Learn more
  - icon:
      src: /icons/zap.svg
    title: 60+ Commands
    details: "Organized across 9 categories — general, admin, group, content, downloader, moderation, fun, utility, and owner commands."
    link: /commands/general
    linkText: Browse commands
  - icon:
      src: /icons/code.svg
    title: Developer Friendly
    details: "Middleware pipeline, type hints, hot-reload, JSON Schema config validation, and a clean architecture that makes extensibility a breeze."
    link: /development/architecture
    linkText: See architecture
  - icon:
      src: /icons/git-pull-request.svg
    title: Contributing
    details: "Want to help? Check out our contribution guide to get started with development, testing, and submitting PRs."
    link: /development/contributing
    linkText: Read guide
---

<div class="terminal-window" data-title="system_stats.sh">
<div class="stats-section">
<div class="stat-item">
<div class="stat-number">60+</div>
<div class="stat-label">Commands</div>
</div>
<div class="stat-item">
<div class="stat-number">9</div>
<div class="stat-label">Categories</div>
</div>
<div class="stat-item">
<div class="stat-number">2</div>
<div class="stat-label">Languages</div>
</div>
</div>
</div>

<div class="home-section">
<div class="terminal-window" data-title="install.sh">
<h2>Quick Start</h2>
<p class="subtitle">$ echo "Get your bot running in under a minute"</p>

<h3>Linux / macOS</h3>

```bash
curl -fsSL https://raw.githubusercontent.com/MhankBarBar/zero-ichi/master/install.sh | bash
```

<h3>Windows (PowerShell)</h3>

```powershell
irm https://raw.githubusercontent.com/MhankBarBar/zero-ichi/master/install.ps1 | iex
```

<p>Then start the bot:</p>

```bash
uv run zero-ichi
# with args:
uv run zero-ichi --debug --dashboard
```

<a href="/getting-started/installation" class="step-link">See full installation guide →</a>
</div>
</div>

<div class="home-section">
<div class="terminal-window" data-title="ls commands/">
<h2>Command Categories</h2>
<p class="subtitle">$ ls -la commands/</p>
<div class="categories-grid">
<a class="category-chip" href="/commands/general">general/</a>
<a class="category-chip" href="/commands/admin">admin/</a>
<a class="category-chip" href="/commands/group">group/</a>
<a class="category-chip" href="/commands/content">content/</a>
<a class="category-chip" href="/commands/downloader">downloader/</a>
<a class="category-chip" href="/commands/moderation">moderation/</a>
<a class="category-chip" href="/commands/fun">fun/</a>
<a class="category-chip" href="/commands/utility">utility/</a>
<a class="category-chip" href="/commands/owner">owner/</a>
</div>
</div>
</div>


