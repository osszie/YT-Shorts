# yt-shorts-agent

Phase 1: Generate 100% original "reddit-vibes" short scripts using the Hugging Face Inference API and save them as JSON. No Reddit API, no uploads, no TTS.

## What this project does
- Picks a theme based on the NICHE and generates an original short story with AITA/confession/relationship/creepy vibes.
- Ensures content is original and suitable for a 30–40s YouTube Shorts narration.
- Saves the output to `output/script.json` in this schema:
  {
    "title": "",
    "description": "",
    "script": ""
  }

## Hugging Face setup
1. Create an account at https://huggingface.co
2. Go to Settings → Access Tokens and create a new Read/Write token.
3. Copy the token and set it in `.env` as HF_API_TOKEN

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

3. Copy `.env.example` to `.env` and add your token:

```bash
cp .env.example .env
# edit .env and set HF_API_TOKEN (required)
# Optionally set MODEL_ID (default: mistralai/Mistral-7B-Instruct-v0.2)
# Optionally set NICHE (options: aita, confession, relationships, creepy; default: aita)
```

## Run

```bash
source .venv/bin/activate
python scripts/agent.py
```

## Notes
- `.env` and `output/` are gitignored; do not commit secrets or generated files.
- This phase only generates scripts; no upload or media creation is implemented.
