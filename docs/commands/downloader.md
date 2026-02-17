# Downloader Commands

Zero Ichi includes a powerful media downloader powered by **yt-dlp**, supporting 1000+ sites including YouTube, TikTok, Instagram, Twitter/X, SoundCloud, and more.

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

::: tip
Reply to the search results or playlist listing with a **number** to select a video.
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
