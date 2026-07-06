# video-bot — YouTube / Instagram transcript fetcher

Paste a video link into a Claude Code session on this repo and Claude will
fetch the transcript + metadata and tell you about the video. The pieces:

- `videobot.py` — CLI that resolves a YouTube or Instagram URL into a markdown
  (or JSON) report: title, uploader, views, duration, description, chapters,
  and the best available transcript (manual captions preferred, auto-generated
  as fallback, with `[m:ss]` timestamps).
- `../../.claude/skills/video-insights/SKILL.md` — the "bot" part: a Claude
  Code skill that auto-triggers when you paste a video link and turns the
  report into a TL;DR + key points + quotes.

## Setup

```bash
pip3 install -r tools/video-bot/requirements.txt   # just yt-dlp
```

**If you use Claude Code on the web / cloud sandboxes:** the environment's
network policy must allow these domains, or all fetches fail with a proxy 403:

- `youtube.com`, `googlevideo.com` (YouTube pages + caption files)
- `instagram.com`, `cdninstagram.com` (Instagram)

Configure this in your Claude Code environment's network settings
(see https://code.claude.com/docs/en/claude-code-on-the-web). Running locally
in the Claude Code CLI needs no special setup.

## Direct CLI usage

```bash
# Markdown report to stdout
python3 tools/video-bot/videobot.py "https://youtu.be/VIDEO_ID"

# Hindi captions, JSON output, saved to a file
python3 tools/video-bot/videobot.py "https://www.youtube.com/watch?v=VIDEO_ID" \
    --lang hi --format json -o report.json

# Instagram reel (most need a logged-in session)
python3 tools/video-bot/videobot.py "https://www.instagram.com/reel/POST_ID/" \
    --cookies-from-browser chrome
```

| Flag | Meaning |
| --- | --- |
| `--lang CODE` | Preferred transcript language (default `en`, falls back sensibly) |
| `--format md\|json` | Output format (default `md`) |
| `--no-timestamps` | Plain transcript text without `[m:ss]` markers |
| `--cookies FILE` | Netscape-format cookies export (Instagram login) |
| `--cookies-from-browser NAME` | Read cookies from a local browser (`chrome`, `firefox`, …) |
| `-o FILE` | Write output to a file instead of stdout |

## Notes and limits

- **YouTube**: works anonymously for public videos. Manual captions are used
  when they exist; otherwise YouTube's auto-generated captions.
- **Instagram**: reels/posts rarely have caption tracks, so the report gives
  metadata + the post caption. Most Instagram URLs also require login cookies.
  For a spoken-word transcript, download the audio (`yt-dlp -x <url>`) and run
  a speech-to-text tool such as `whisper` on it.
- Tests (offline, no network needed): `cd tools/video-bot && python3 test_videobot.py`
