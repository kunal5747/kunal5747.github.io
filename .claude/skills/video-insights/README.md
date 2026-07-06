# video-insights — YouTube / Instagram transcript bot

Paste a video link into Claude and it fetches the transcript + metadata and
tells you about the video. This folder is a self-contained Claude skill:

- `SKILL.md` — instructions Claude follows when it sees a video link.
- `videobot.py` — CLI that resolves a YouTube or Instagram URL into a markdown
  (or JSON) report: title, uploader, views, duration, description, chapters,
  and the best available transcript (manual captions preferred, auto-generated
  as fallback, with `[m:ss]` timestamps).
- `test_videobot.py` — offline tests (`python3 test_videobot.py`).

## Where it works

- **Claude Code on this repo** (CLI, web, desktop): works automatically — the
  skill is picked up from `.claude/skills/`.
- **Every Claude Code session, any repo**: copy this folder to
  `~/.claude/skills/video-insights/` on your machine.
- **Claude chat (claude.ai) and Cowork**: zip this folder and upload it as a
  custom skill under Settings → Capabilities → Skills.

## Setup

```bash
pip3 install yt-dlp
```

**Cloud sandboxes** (Claude Code on the web): the environment's network policy
must allow `youtube.com`, `googlevideo.com`, `instagram.com`, and
`cdninstagram.com`, or fetches fail with a proxy 403. Configure this in the
environment's network settings (https://code.claude.com/docs/en/claude-code-on-the-web).
Local sessions need no special setup.

## Direct CLI usage

```bash
# Markdown report to stdout
python3 videobot.py "https://youtu.be/VIDEO_ID"

# Hindi captions, JSON output, saved to a file
python3 videobot.py "https://www.youtube.com/watch?v=VIDEO_ID" --lang hi --format json -o report.json

# Instagram reel (most need a logged-in session)
python3 videobot.py "https://www.instagram.com/reel/POST_ID/" --cookies-from-browser chrome
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
