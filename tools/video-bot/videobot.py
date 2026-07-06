#!/usr/bin/env python3
"""videobot: fetch metadata + transcript for a YouTube or Instagram video URL.

Usage:
    python3 videobot.py <url> [--lang en] [--format md|json] [--no-timestamps]
                              [--cookies FILE | --cookies-from-browser BROWSER]
                              [-o OUTPUT_FILE]

Outputs a markdown report (default) or JSON with:
  - video metadata (title, uploader, duration, views, upload date, description, ...)
  - the best available transcript (manual captions preferred over auto-generated)

Requires: yt-dlp  (pip install yt-dlp)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field


# --------------------------------------------------------------------------
# URL detection
# --------------------------------------------------------------------------

YOUTUBE_RE = re.compile(
    r"""(?x)
    (?:https?://)?
    (?:
        (?:www\.|m\.|music\.)?youtube\.com/
            (?:watch\?(?:[^#\s]*&)?v=|shorts/|live/|embed/|v/)
        |
        youtu\.be/
    )
    (?P<id>[A-Za-z0-9_-]{11})
    """
)

INSTAGRAM_RE = re.compile(
    r"""(?x)
    (?:https?://)?
    (?:www\.)?instagram\.com/
    (?:[A-Za-z0-9_.]+/)?          # optional username prefix (e.g. /user/reel/ID)
    (?P<kind>p|reel|reels|tv)/
    (?P<id>[A-Za-z0-9_-]+)
    """
)


def detect_platform(url: str) -> tuple[str, str] | None:
    """Return (platform, video_id) or None if the URL is not recognised."""
    m = YOUTUBE_RE.search(url)
    if m:
        return ("youtube", m.group("id"))
    m = INSTAGRAM_RE.search(url)
    if m:
        return ("instagram", m.group("id"))
    return None


# --------------------------------------------------------------------------
# Subtitle parsing (json3 and WebVTT)
# --------------------------------------------------------------------------

@dataclass
class Cue:
    start: float  # seconds
    text: str


def parse_json3(raw: str) -> list[Cue]:
    """Parse YouTube's json3 subtitle format into cues."""
    data = json.loads(raw)
    cues: list[Cue] = []
    for event in data.get("events", []):
        segs = event.get("segs")
        if not segs:
            continue
        text = "".join(seg.get("utf8", "") for seg in segs)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        start = event.get("tStartMs", 0) / 1000.0
        cues.append(Cue(start, text))
    return cues


_VTT_TS_RE = re.compile(
    r"(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})\s*-->"
)
_VTT_TAG_RE = re.compile(r"<[^>]+>")


def parse_vtt(raw: str) -> list[Cue]:
    """Parse WebVTT (or SRT-ish) subtitles into cues, deduping rolling captions."""
    cues: list[Cue] = []
    current_start: float | None = None
    last_text = ""
    for line in raw.splitlines():
        line = line.strip("﻿").strip()
        m = _VTT_TS_RE.match(line)
        if m:
            h = int(m.group(1) or 0)
            current_start = h * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(4)) / 1000.0
            continue
        if not line or line == "WEBVTT" or line.startswith(("NOTE", "STYLE", "Kind:", "Language:")) or line.isdigit():
            continue
        if current_start is None:
            continue
        text = _VTT_TAG_RE.sub("", line)
        text = re.sub(r"\s+", " ", text).strip()
        # Auto-captions roll: each cue repeats the previous line. Skip repeats.
        if not text or text == last_text:
            continue
        cues.append(Cue(current_start, text))
        last_text = text
    return cues


def format_ts(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def cues_to_text(cues: list[Cue], timestamps: bool = True, block_seconds: int = 30) -> str:
    """Join cues into readable paragraphs, one timestamped block per ~block_seconds."""
    if not cues:
        return ""
    if not timestamps:
        return " ".join(c.text for c in cues)
    lines: list[str] = []
    block_start = cues[0].start
    block_parts: list[str] = []
    for cue in cues:
        if cue.start - block_start >= block_seconds and block_parts:
            lines.append(f"[{format_ts(block_start)}] {' '.join(block_parts)}")
            block_start = cue.start
            block_parts = []
        block_parts.append(cue.text)
    if block_parts:
        lines.append(f"[{format_ts(block_start)}] {' '.join(block_parts)}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Fetching via yt-dlp
# --------------------------------------------------------------------------

@dataclass
class VideoReport:
    platform: str
    url: str
    metadata: dict = field(default_factory=dict)
    transcript_lang: str | None = None
    transcript_kind: str | None = None  # "manual" | "auto"
    transcript: str = ""
    chapters: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


LANG_FALLBACKS = ["en", "en-US", "en-GB", "en-IN", "hi", "hi-en"]

METADATA_KEYS = [
    "id", "title", "fulltitle", "uploader", "channel", "channel_follower_count",
    "upload_date", "duration", "duration_string", "view_count", "like_count",
    "comment_count", "description", "tags", "categories", "webpage_url",
    "thumbnail", "language", "live_status", "availability",
]


def _pick_track(tracks: dict, preferred: str) -> tuple[str, list[dict]] | None:
    """Pick the best language track from a yt-dlp subtitles dict."""
    if not tracks:
        return None
    candidates = [preferred] + LANG_FALLBACKS
    for lang in candidates:
        if lang in tracks:
            return lang, tracks[lang]
        # prefix match, e.g. preferred "en" matches "en-orig"
        for key in tracks:
            if key.split("-")[0] == lang.split("-")[0]:
                return key, tracks[key]
    first = next(iter(tracks))
    return first, tracks[first]


def _download_subtitle(ydl, formats: list[dict]) -> list[Cue] | None:
    """Download and parse a subtitle track, preferring json3 over vtt."""
    by_ext = {f.get("ext"): f for f in formats if f.get("url")}
    for ext in ("json3", "vtt", "srv3", "srt", "ttml"):
        fmt = by_ext.get(ext)
        if not fmt:
            continue
        try:
            raw = ydl.urlopen(fmt["url"]).read().decode("utf-8", "replace")
        except Exception:
            continue
        try:
            if ext == "json3":
                return parse_json3(raw)
            return parse_vtt(raw)
        except Exception:
            continue
    return None


def fetch_report(url: str, lang: str, cookies: str | None,
                 cookies_from_browser: str | None, timestamps: bool) -> VideoReport:
    try:
        import yt_dlp  # noqa: PLC0415
    except ImportError:
        sys.exit("yt-dlp is not installed. Run: pip install yt-dlp")

    detected = detect_platform(url)
    platform = detected[0] if detected else "unknown"
    report = VideoReport(platform=platform, url=url)
    if not detected:
        report.warnings.append(
            "URL not recognised as YouTube or Instagram; attempting a generic yt-dlp extraction."
        )

    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": [lang, "en.*", "all"],
        "extractor_retries": 2,
    }
    if cookies:
        opts["cookiefile"] = cookies
    if cookies_from_browser:
        opts["cookiesfrombrowser"] = (cookies_from_browser,)

    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as exc:
            msg = str(exc)
            hints = []
            if "403" in msg or "proxy" in msg.lower() or "Tunnel connection" in msg:
                hints.append(
                    "Network blocked: if running in a Claude Code cloud environment, allow "
                    "youtube.com, googlevideo.com, instagram.com and cdninstagram.com in the "
                    "environment's network policy, or run this locally."
                )
            if platform == "instagram" and ("login" in msg.lower() or "rate" in msg.lower() or "empty" in msg.lower()):
                hints.append(
                    "Instagram often requires login: retry with --cookies <exported-cookies.txt> "
                    "or --cookies-from-browser chrome."
                )
            sys.exit("Failed to fetch video info: " + msg + ("\n" + "\n".join(hints) if hints else ""))

        # Playlist/multi-entry URLs: take the first entry.
        if info.get("_type") == "playlist" and info.get("entries"):
            info = info["entries"][0]

        report.metadata = {k: info.get(k) for k in METADATA_KEYS if info.get(k) is not None}
        report.chapters = [
            {"start": c.get("start_time"), "title": c.get("title")}
            for c in (info.get("chapters") or [])
        ]

        cues: list[Cue] | None = None
        manual = _pick_track(info.get("subtitles") or {}, lang)
        if manual:
            cues = _download_subtitle(ydl, manual[1])
            if cues:
                report.transcript_lang, report.transcript_kind = manual[0], "manual"
        if not cues:
            auto = _pick_track(info.get("automatic_captions") or {}, lang)
            if auto:
                cues = _download_subtitle(ydl, auto[1])
                if cues:
                    report.transcript_lang, report.transcript_kind = auto[0], "auto"

        if cues:
            report.transcript = cues_to_text(cues, timestamps=timestamps)
        else:
            if platform == "instagram":
                report.warnings.append(
                    "No caption track available (typical for Instagram). The post caption is in "
                    "metadata['description']. For a spoken-word transcript, download the audio "
                    "(yt-dlp -x) and run a speech-to-text tool such as whisper."
                )
            else:
                report.warnings.append("No manual or auto-generated captions found for this video.")

    return report


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def to_markdown(r: VideoReport) -> str:
    md = r.metadata
    lines = [f"# {md.get('title', 'Unknown title')}", ""]
    facts = [
        ("Platform", r.platform),
        ("Uploader", md.get("uploader") or md.get("channel")),
        ("Duration", md.get("duration_string")),
        ("Views", md.get("view_count")),
        ("Likes", md.get("like_count")),
        ("Comments", md.get("comment_count")),
        ("Uploaded", md.get("upload_date")),
        ("URL", md.get("webpage_url") or r.url),
    ]
    for label, value in facts:
        if value is not None:
            lines.append(f"- **{label}:** {value}")
    if md.get("tags"):
        lines.append(f"- **Tags:** {', '.join(md['tags'][:15])}")
    if md.get("description"):
        lines += ["", "## Description", "", md["description"].strip()]
    if r.chapters:
        lines += ["", "## Chapters", ""]
        for c in r.chapters:
            lines.append(f"- [{format_ts(c['start'] or 0)}] {c['title']}")
    lines += ["", "## Transcript"]
    if r.transcript:
        lines.append(f"_({r.transcript_kind} captions, language: {r.transcript_lang})_")
        lines += ["", r.transcript]
    else:
        lines += ["", "_No transcript available._"]
    if r.warnings:
        lines += ["", "## Warnings", ""]
        lines += [f"- {w}" for w in r.warnings]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch metadata + transcript for a YouTube/Instagram video.")
    ap.add_argument("url", help="YouTube or Instagram video URL")
    ap.add_argument("--lang", default="en", help="Preferred transcript language code (default: en)")
    ap.add_argument("--format", choices=["md", "json"], default="md", dest="fmt")
    ap.add_argument("--no-timestamps", action="store_true", help="Plain transcript text without [m:ss] markers")
    ap.add_argument("--cookies", help="Path to a Netscape-format cookies file (needed for most Instagram posts)")
    ap.add_argument("--cookies-from-browser", help="Browser to read cookies from (chrome, firefox, ...)")
    ap.add_argument("-o", "--output", help="Write result to this file instead of stdout")
    args = ap.parse_args()

    report = fetch_report(
        args.url, args.lang, args.cookies, args.cookies_from_browser,
        timestamps=not args.no_timestamps,
    )

    if args.fmt == "json":
        out = json.dumps(report.__dict__, ensure_ascii=False, indent=2, default=str)
    else:
        out = to_markdown(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(out)
        print(f"Wrote {args.output}")
    else:
        print(out)


if __name__ == "__main__":
    main()
