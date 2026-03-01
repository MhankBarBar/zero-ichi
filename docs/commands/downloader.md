# Downloader Commands

Zero Ichi includes a powerful media downloader powered by **yt-dlp**, supporting 1000+ sites including YouTube, TikTok, Instagram, Twitter/X, SoundCloud, and more. It also supports **Apple Music** downloads.

For image-post extraction (`/photo`), Zero Ichi uses **gallery-dl**.

::: warning YouTube Requirement
**[Bun](https://bun.sh)** must be installed on your server for YouTube downloads to work. yt-dlp uses it to solve YouTube's JS challenges.

```bash
curl -fsSL https://bun.sh/install | bash
```
:::

::: warning Photo Requirement
Install **gallery-dl** for `/photo` and `/autodl mode photo`:

```bash
pip install gallery-dl
```

If your target site requires login/session cookies, configure `downloader.gallery_dl` in `config.json`:

```json
{
  "downloader": {
    "gallery_dl": {
      "config_file": "",
      "config": {},
      "cookies_file": "data/gallery-cookies.txt",
      "cookies_from_browser": "",
      "extra_args": []
    }
  }
}
```

You can also put full gallery-dl options in `downloader.gallery_dl.config` (same JSON structure as the official gallery-dl configuration docs).

This maps to gallery-dl runtime flags such as `--config`, `--cookies`, and `--cookies-from-browser`.
:::

## Commands

### `/dl <url>` or `/dl <query>`

**Download media or search YouTube.**

**1. Direct Download:**
Send with a URL to get quality options:
```
/dl https://youtube.com/watch?v=dQw4w9WgXcQ
```

**2. YouTube Search:**
Search for a video:
```
/dl Never Gonna Give You Up
```
*Returns a list of top 5 results.*

**3. Custom Search Count:**
Get more results (up to 20):
```
/dl -n 10 rick roll
```

**4. Playlists:**
Paste a playlist URL to list tracks:
```
/dl https://youtube.com/playlist?list=...
```

---

### `/am <url>`

**Download from Apple Music.**

**1. Single Song:**
```
/am https://music.apple.com/album/song-name/123?i=456
```

**2. Album:**
Paste an album URL to list all tracks:
```
/am https://music.apple.com/album/album-name/123
```

---

### `/photo <url>`

**Download image posts/albums from supported sites (gallery-dl).**

- If 1 image is found, the bot sends a single image.
- If multiple images are found, the bot sends them as a **media album**.
- WEBP images are automatically converted before sending for better WhatsApp compatibility.
- Caption includes post details when available (description, username, likes).

```
/photo https://www.instagram.com/p/xxxxxxxxx/
```

---

### Selection Options

When the bot shows a numbered list (search results, playlists, or albums), reply with:

| Format | Example | What it does |
|--------|---------|-------------|
| Single | `3` | Download track #3 |
| Range | `1-5` | Download tracks 1 through 5 |
| List | `1, 3, 5` | Download specific tracks |
| Mixed | `1-3, 7, 9-12` | Combine ranges and numbers |
| All | `all` or `0` | Download every track |

::: tip Batch Downloads in Groups
When downloading multiple tracks in a **group chat**, files are sent to your **DM** to avoid spamming the group. In private chats, files are sent directly.

There's a **5-second cooldown** between each track to prevent rate limiting.
:::

---

### `/audio <url>`

**Quick audio download** — automatically picks the best audio quality and converts to MP3.

```
/audio https://youtube.com/watch?v=dQw4w9WgXcQ
```

**Aliases**: `/mp3`, `/music`

---

### `/video <url>`

**Quick video download** — automatically picks the best video quality within the file size limit.

```
/video https://youtube.com/watch?v=dQw4w9WgXcQ
```

**Aliases**: `/vid`, `/mp4`

---

### `/cancel [all]`

**Cancel an active download.**

- **`/cancel`**: Cancels your own active download in the current chat.
- **`/cancel all`**: Cancels **all** active downloads in the current chat (requires Admin or Owner permission).

::: tip Partial Files
Cancelled downloads are automatically cleaned up — no partial `.part` files are left on the server.
:::

---

### Auto Link Download (Owner Config)

You can enable automatic link download (without sending `/dl`) using owner config command:

```
/autodl on
/autodl mode auto
/autodl mode photo
/autodl cooldown 30
/autodl maxlinks 1
/autodl album 10
/autodl photolimit 20
```

Behavior notes:

- Uses the same downloader engine and size limits as manual `/dl` flow.
- Apple Music links are auto-routed to the Apple Music downloader pipeline (not yt-dlp).
- Supports `auto`, `audio`, `video`, or `photo` selection mode.
- Photo mode uses gallery-dl and sends multi-image results as albums.
- In group moderation setups, anti-link rules run first.

---

## Supported Sites

yt-dlp supports **1000+ sites** including:

| Platform | Example URL |
|----------|-------------|
| YouTube | `https://youtube.com/watch?v=...` |
| TikTok | `https://tiktok.com/@user/video/...` |
| Instagram | `https://instagram.com/reel/...` |
| Twitter/X | `https://x.com/user/status/...` |
| SoundCloud | `https://soundcloud.com/artist/track` |
| Reddit | `https://reddit.com/r/sub/comments/...` |
| Facebook | `https://facebook.com/watch?v=...` |
| Twitch | `https://twitch.tv/videos/...` |
| Apple Music | `https://music.apple.com/album/...` |

> [!TIP]
> For a complete list of yt-dlp sites, see [yt-dlp supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

## Limits

- **Max file size**: 180 MB (WhatsApp limit)
- **Cooldown**: 10–15 seconds per user to prevent spam
- **Batch cooldown**: 5 seconds between each track
- **Selection expires**: 5 minutes after showing options
- Files are automatically cleaned up after sending

## Troubleshooting

### "Sign in to confirm you're not a bot" / YouTube captcha

This is common on VPS environments. To resolve it:

1. **Install Bun**: yt-dlp uses Bun to execute YouTube's JS challenges:
   ```bash
   curl -fsSL https://bun.sh/install | bash
   ```
2. **Use Cookies**: Follow the [Cookie Setup Guide](/getting-started/configuration#youtube-cookies) to provide browser cookies.
3. **Verify Bun is in PATH**: After installing, make sure `bun --version` works in your shell. You may need to restart your shell or add `~/.bun/bin` to `$PATH`.
