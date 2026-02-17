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

<div class="home-section">
  <h2>Quick Start</h2>
  <p class="subtitle">Get your bot running in 3 steps</p>

  <div class="quick-steps">
    <div class="step-card">
      <div class="step-number">1</div>
      <h3>Install</h3>
      <p>Clone the repo and install dependencies with <code>uv sync</code></p>
    </div>
    <div class="step-card">
      <div class="step-number">2</div>
      <h3>Configure</h3>
      <p>Edit <code>config.json</code> and set your prefix, owner number, and API keys</p>
    </div>
    <div class="step-card">
      <div class="step-number">3</div>
      <h3>Run</h3>
      <p>Start with <code>uv run main.py</code> and scan the QR code with WhatsApp</p>
    </div>
  </div>
</div>

<div class="home-section">
  <h2>Command Categories</h2>
  <p class="subtitle">Everything you need, organized neatly</p>

  <div class="categories-grid">
    <a class="category-chip" href="/commands/general">General</a>
    <a class="category-chip" href="/commands/admin">Admin</a>
    <a class="category-chip" href="/commands/group">Group</a>
    <a class="category-chip" href="/commands/content">Content</a>
    <a class="category-chip" href="/commands/downloader">Downloader</a>
    <a class="category-chip" href="/commands/moderation">Moderation</a>
    <a class="category-chip" href="/commands/fun">Fun</a>
    <a class="category-chip" href="/commands/utility">Utility</a>
    <a class="category-chip" href="/commands/owner">Owner</a>
  </div>
</div>
