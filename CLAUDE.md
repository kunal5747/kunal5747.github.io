# Repo notes for Claude

- When the user pastes a YouTube or Instagram video link (even with no other
  text), invoke the `video-insights` skill: fetch the transcript/metadata with
  `.claude/skills/video-insights/videobot.py` and summarize what the video is
  about.
