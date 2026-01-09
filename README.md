# yt-shorts-agent

Phase 1: Generate 100% original "reddit-vibes" short scripts using OpenAI and save them as JSON. No Reddit API, no uploads, no TTS.

## What this project does
- Picks a theme based on the NICHE and generates an original short story with AITA/confession/relationship vibes.
- Ensures content is original and suitable for a 30–40s YouTube Shorts narration.
- Saves the output to `output/script.json` in this schema:
  {
    "title": "",
    "description": "",
    "script": ""
  }

## Setup
1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and add your OpenAI API key:

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY
```

Required environment variables in `.env`:
- OPENAI_API_KEY
- CHANNEL_STYLE (defaults to reddit_vibes)
- NICHE (e.g. aita, confession, relationships, creepy)

## Run

```bash
source .venv/bin/activate
python scripts/agent.py
```

## Notes
- `.env` and `output/` are gitignored; do not commit secrets or generated files.
- This phase only generates scripts; no upload or media creation is implemented.
