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

---
<div class="home-section">
<h2>Quick Start</h2>

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
uv run zero-ichi setup
uv run zero-ichi
# with args:
uv run zero-ichi --debug --dashboard
```

<a href="/getting-started/installation" class="step-link">See full installation guide →</a>
</div>

<div class="home-section">
<h2>Command Categories</h2>
<div class="categories-grid">
<a class="category-chip" href="/commands/general">general</a>
<a class="category-chip" href="/commands/admin">admin</a>
<a class="category-chip" href="/commands/group">group</a>
<a class="category-chip" href="/commands/content">content</a>
<a class="category-chip" href="/commands/downloader">downloader</a>
<a class="category-chip" href="/commands/moderation">moderation</a>
<a class="category-chip" href="/commands/fun">fun</a>
<a class="category-chip" href="/commands/utility">utility</a>
<a class="category-chip" href="/commands/owner">owner</a>
</div>
</div>
