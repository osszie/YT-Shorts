# yt-shorts-agent

Phase 1: Generate 100% original "reddit-vibes" short scripts using Ollama (local AI) and save them as JSON. No Reddit API, no uploads, no TTS.

## What this project does
- Picks a theme based on the NICHE and generates an original short story with AITA/confession/relationship/creepy vibes.
- Uses Ollama with phi3:mini model running locally (no API costs!)
- Ensures content is original and suitable for a 30–40s YouTube Shorts narration.
- Saves the output to `output/script.json` in this schema:
  ```json
  {
    "title": "",
    "description": "",
    "script": ""
  }
  ```

## Prerequisites
- Python 3.7+
- Ollama installed and running locally
- phi3:mini model downloaded (or another model of your choice)

## Ollama Setup
1. Install Ollama from https://ollama.ai
2. Start Ollama server:
   ```bash
   ollama serve
   ```
3. Pull the phi3:mini model:
   ```bash
   ollama pull phi3:mini
   ```
4. Verify it's working:
   ```bash
   ollama list
   ```

## Project Setup
1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` (optional - defaults work if Ollama is running locally):
   ```bash
   cp .env.example .env
   # Edit .env if you need to change:
   # - OLLAMA_BASE_URL (default: http://localhost:11434)
   # - MODEL_NAME (default: phi3:mini)
   # - NICHE (options: aita, confession, relationships, creepy; default: aita)
   ```

## Run
```bash
source .venv/bin/activate
python scripts/agent.py
```

The script will:
- Pick a random theme based on your NICHE setting
- Generate a unique Reddit-style story
- Save it to `output/script.json`
- Print a preview to the terminal

## Notes
- `.env` and `output/` are gitignored; do not commit secrets or generated files.
- This phase only generates scripts; no upload or media creation is implemented.
- Ollama runs locally, so no API costs and your data stays private.
- Models are stored locally (can be configured to use external storage).
