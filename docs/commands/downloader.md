# Downloader Commands

Zero Ichi includes a powerful media downloader powered by **yt-dlp**, supporting 1000+ sites including YouTube, TikTok, Instagram, Twitter/X, SoundCloud, and more.

## Commands

### `/dl <url>`

**Download with quality selection.**

Send the command with a URL:
```
/dl https://youtube.com/watch?v=dQw4w9WgXcQ
```

The bot responds with media details and numbered quality options:

```
✦ Never Gonna Give You Up
→ Rick Astley • YouTube
⏱ 3:33

▷ Video
  • 1 → 1080p MP4 ~25.3MB
  • 2 → 720p MP4 ~12.1MB
  • 3 → 480p MP4 ~6.8MB

♫ Audio
  • 4 → 256kbps WEBM ~5.6MB
  • 5 → 128kbps M4A ~3.1MB

ⓘ Reply to this message with the number to download.
```

**Reply** to that message with the number to start downloading:
```
2
```

::: tip
Only the person who sent the `/dl` command can reply to select a format. Other users' replies are ignored.
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

> [!TIP]
> For a complete list, see [yt-dlp supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).

## Limits

- **Max file size**: 180 MB (WhatsApp limit)
- **Cooldown**: 10–15 seconds per user to prevent spam
- **Selection expires**: 5 minutes after showing options
- Files are automatically cleaned up after sending

> [!NOTE]
> If a video exceeds the size limit, try `/audio` instead — audio files are much smaller.
