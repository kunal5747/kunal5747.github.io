# Repo notes for Claude

- When the user pastes a YouTube or Instagram video link (even with no other
  text), invoke the `video-insights` skill: fetch the transcript/metadata with
  `.claude/skills/video-insights/videobot.py` and summarize what the video is
  about.
- The user runs a 3-partner construction JV business in India. His finance
  playbooks, templates, deal model, and coaching journal live in
  `finance-kit/`. For any finance/deal/loan/fundraising question — or a
  scheduled coaching session — invoke the `finance-coach` skill and use his
  real numbers from `finance-kit/journal/progress.md`.
