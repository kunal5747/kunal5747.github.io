# Repo notes for Claude

- When the user pastes a YouTube or Instagram video link (even with no other
  text), invoke the `video-insights` skill: fetch the transcript/metadata with
  `tools/video-bot/videobot.py` and summarize what the video is about.
