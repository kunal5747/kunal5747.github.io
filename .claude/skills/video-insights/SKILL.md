---
name: video-insights
description: >-
  Fetch the transcript and metadata of a YouTube or Instagram video and explain
  what the video is about. Use this whenever the user pastes a YouTube link
  (youtube.com/watch, youtu.be, youtube.com/shorts) or an Instagram link
  (instagram.com/reel, /p/, /tv/) — even with no other text — or asks to
  summarize, transcribe, or answer questions about a video.
---

# Video Insights

The user pasted a video link (or asked about a video). Fetch its transcript and
metadata with the bundled tool, then tell them about the video.

## Steps

1. **Ensure yt-dlp is installed**: `python3 -m yt_dlp --version` — if missing,
   run `pip3 install --user -r tools/video-bot/requirements.txt`.

2. **Fetch** (transcripts can be long — always write to the scratchpad, never
   stdout):

   ```bash
   python3 tools/video-bot/videobot.py "<URL>" -o <scratchpad>/video.md
   ```

   Useful flags: `--lang <code>` for non-English videos, `--format json` for
   structured output, `--cookies <file>` / `--cookies-from-browser chrome` for
   Instagram posts that require login.

3. **Read** the output file. If the transcript is very long, read it in chunks
   (offset/limit) rather than all at once.

4. **Reply** with, in this order:
   - **TL;DR** — 2–3 sentences on what the video is about.
   - **Key points** — bulleted takeaways, with `[m:ss]` timestamps when the
     transcript has them.
   - **Notable quotes** — 1–3 verbatim lines if any stand out.
   - **Details** — uploader, duration, views, upload date (one compact line).
   - Offer to answer follow-up questions, extract specific sections, or save
     the full transcript somewhere.

## Failure modes

- **Proxy/403 or "Tunnel connection failed"**: the sandbox's network policy
  blocks the site. Tell the user to allow `youtube.com`, `googlevideo.com`,
  `instagram.com`, and `cdninstagram.com` in their Claude Code environment's
  network settings (or run the tool locally), then stop — don't retry.
- **Instagram "login required" / empty response**: ask the user for a cookies
  export (`--cookies`), and explain that most Instagram content needs an
  authenticated session.
- **No captions available**: summarize from the title, description, and
  chapters instead, and say clearly that no transcript exists. For Instagram
  reels the post caption (in the Description section) is usually the best
  available text.
