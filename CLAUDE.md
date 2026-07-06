# Repo notes for Claude

- When the user pastes a YouTube or Instagram video link (even with no other
  text), invoke the `video-insights` skill: fetch the transcript/metadata with
  `.claude/skills/video-insights/videobot.py` and summarize what the video is
  about.
- The user's finance material lives in the PRIVATE repo
  `kunal5747/business-private` (add it to the session if needed). Do not
  store business/deal numbers in this public repo.
- Style: minimum tokens, maximum efficiency. Short answers, numbers first,
  no repetition. Expand only when asked.
