# yt-shorts-agent

A simple Python agent that pulls a story-style Reddit post, rewrites it using the OpenAI API into a short script suitable for YouTube Shorts, and saves the result as JSON. Phase 1 only: no uploading or media generation.

## What it does
- Fetches a random non-NSFW, non-stickied, text-heavy post from one of: TrueOffMyChest, AmItheAsshole, relationship_advice
- Sends the post text to OpenAI to rewrite into a 30–40s (90–130 words) short script
- Saves the output to `output/script.json`

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

3. Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
# then edit .env to add your keys
```

Required environment variables in `.env`:
- OPENAI_API_KEY
- REDDIT_CLIENT_ID
- REDDIT_CLIENT_SECRET
- REDDIT_USER_AGENT (defaults to yt-shorts-agent)

## Run

```bash
source .venv/bin/activate
python scripts/agent.py
```

## Notes
- Do NOT commit `.env` or `output/` to version control. They are in `.gitignore`.
- This phase only generates scripts; no upload or media creation is implemented.
