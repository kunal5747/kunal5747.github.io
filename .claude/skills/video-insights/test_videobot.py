"""Offline tests for videobot's URL detection and subtitle parsing.

Run: python3 tools/video-bot/test_videobot.py
"""

import json

from videobot import Cue, cues_to_text, detect_platform, format_ts, parse_json3, parse_vtt


def test_detect_platform():
    cases = {
        "https://www.youtube.com/watch?v=jNQXAC9IVRw": ("youtube", "jNQXAC9IVRw"),
        "https://www.youtube.com/watch?t=10&v=jNQXAC9IVRw": ("youtube", "jNQXAC9IVRw"),
        "https://youtu.be/jNQXAC9IVRw?si=abc": ("youtube", "jNQXAC9IVRw"),
        "https://www.youtube.com/shorts/abcDEF12345": ("youtube", "abcDEF12345"),
        "https://m.youtube.com/watch?v=jNQXAC9IVRw": ("youtube", "jNQXAC9IVRw"),
        "https://www.youtube.com/live/jNQXAC9IVRw": ("youtube", "jNQXAC9IVRw"),
        "https://www.instagram.com/reel/C8xYz12AbCd/": ("instagram", "C8xYz12AbCd"),
        "https://www.instagram.com/p/C8xYz12AbCd/?igsh=x": ("instagram", "C8xYz12AbCd"),
        "https://instagram.com/someuser/reel/C8xYz12AbCd/": ("instagram", "C8xYz12AbCd"),
        "https://www.instagram.com/tv/C8xYz12AbCd/": ("instagram", "C8xYz12AbCd"),
        "https://example.com/watch?v=nope": None,
    }
    for url, expected in cases.items():
        got = detect_platform(url)
        assert got == expected, f"{url}: expected {expected}, got {got}"


def test_parse_json3():
    raw = json.dumps({
        "events": [
            {"tStartMs": 0, "dDurationMs": 2000},  # no segs -> skipped
            {"tStartMs": 500, "segs": [{"utf8": "hello "}, {"utf8": "world"}]},
            {"tStartMs": 3000, "segs": [{"utf8": "\n"}]},  # whitespace only -> skipped
            {"tStartMs": 65000, "segs": [{"utf8": "second  minute"}]},
        ]
    })
    cues = parse_json3(raw)
    assert [c.text for c in cues] == ["hello world", "second minute"], cues
    assert cues[0].start == 0.5 and cues[1].start == 65.0


def test_parse_vtt():
    raw = """WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:03.000
<c>hello</c> there

00:00:03.000 --> 00:00:05.000
hello there

00:00:05.000 --> 00:00:07.000
next line

01:00:05.000 --> 01:00:07.000
after an hour
"""
    cues = parse_vtt(raw)
    # rolling duplicate "hello there" deduped
    assert [c.text for c in cues] == ["hello there", "next line", "after an hour"], cues
    assert cues[0].start == 1.0
    assert cues[2].start == 3605.0


def test_cues_to_text():
    cues = [Cue(0, "a"), Cue(10, "b"), Cue(35, "c"), Cue(70, "d")]
    out = cues_to_text(cues, timestamps=True, block_seconds=30)
    assert out == "[0:00] a b\n[0:35] c\n[1:10] d", repr(out)
    assert cues_to_text(cues, timestamps=False) == "a b c d"
    assert cues_to_text([], timestamps=True) == ""


def test_format_ts():
    assert format_ts(0) == "0:00"
    assert format_ts(65) == "1:05"
    assert format_ts(3661) == "1:01:01"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"ok  {name}")
    print("All tests passed.")
