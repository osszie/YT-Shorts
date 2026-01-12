# yt-shorts-agent

Automated YouTube Shorts content generation pipeline using local AI. Generates original Reddit-style stories, converts them to voice, and creates vertical videos with captions.

## Current Status: Phase 1, 2, 3, & 4 Complete ✅

### Phase 1: Story Generation ✅
- Generates 100% original Reddit-style stories using Ollama (phi3:mini)
- Outputs JSON with title, description, and script

### Phase 2: Voice Synthesis ✅
- Converts script to MP3 audio using Microsoft Edge TTS (free)
- Configurable voice, rate, and pitch

### Phase 3: Video Generation ✅
- Creates timed SRT captions from script and audio
- Renders 1080x1920 vertical video with background, voice, and burned-in captions

### Phase 4: YouTube Upload ✅
- Automated upload to YouTube via YouTube Data API v3
- Metadata management (title, description, tags from script.json)
- Scheduling support for delayed publishing
- OAuth2 authentication with token persistence

## Prerequisites
- Python 3.7+
- Ollama installed and running locally
- phi3:mini model downloaded
- FFmpeg installed (`brew install ffmpeg` on macOS)
- Google Cloud Project with YouTube Data API v3 enabled (for Phase 4)

## Setup

### 1. Install Ollama
1. Install from https://ollama.ai
2. Start Ollama server:
   ```bash
   ollama serve
   ```
3. Pull the phi3:mini model:
   ```bash
   ollama pull phi3:mini
   ```

### 2. Install FFmpeg (macOS)
```bash
brew install ffmpeg
```

### 3. Project Setup
1. Create and activate virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` (optional - defaults work):
   ```bash
   cp .env.example .env
   ```

4. Add background videos:
   - Place `.mp4` files in `assets/backgrounds/`
   - Videos will be randomly selected for each render
   - Any resolution works (will be cropped/scaled to 1080x1920)

5. Set up YouTube API (for Phase 4):
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project or select an existing one
   - Enable YouTube Data API v3
   - Create OAuth 2.0 credentials (Desktop app type)
   - Download credentials and save as `credentials.json` in project root
   - On first run, you'll be prompted to authorize the app in your browser

## Usage

### Full Pipeline
Run all phases in sequence:

```bash
source .venv/bin/activate

# Phase 1: Generate story
python scripts/agent.py

# Phase 2: Generate voice
python scripts/tts.py

# Phase 3a: Generate captions
python scripts/captions.py

# Phase 3b: Render video
python scripts/render.py

# Phase 4: Upload to YouTube
python scripts/upload.py
```

### Output Files
All generated files are in `output/` (gitignored):
- `script.json` - Generated story (title, description, script)
- `voice.mp3` - Audio narration
- `captions.srt` - Timed subtitles
- `final.mp4` - Final 1080x1920 video with captions

## Configuration

### Environment Variables (`.env`)
```bash
# Ollama settings
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=phi3:mini
NICHE=aita  # Options: aita, confession, relationships, creepy

# TTS settings
TTS_VOICE=en-US-GuyNeural
TTS_RATE=+5%
TTS_PITCH=+0Hz

# YouTube upload settings (Phase 4)
YOUTUBE_CATEGORY_ID=22  # People & Blogs (see YouTube category IDs)
YOUTUBE_PRIVACY=private  # Options: private, unlisted, public
YOUTUBE_TAGS=shorts,reddit,story,aita
SCHEDULE_HOURS=0  # Hours to wait before publishing (0 = immediate)
```

### Background Videos
- Add `.mp4` files to `assets/backgrounds/`
- Videos are randomly selected for each render
- Will be looped and cropped/scaled to 1080x1920 (9:16 aspect ratio)
- Center crop is used to maintain aspect ratio

## Project Structure
```
yt-shorts-agent/
├── scripts/
│   ├── agent.py      # Phase 1: Story generation
│   ├── tts.py         # Phase 2: Voice synthesis
│   ├── captions.py    # Phase 3a: Caption generation
│   ├── render.py      # Phase 3b: Video rendering
│   └── upload.py      # Phase 4: YouTube upload
├── assets/
│   └── backgrounds/   # Background video files (.mp4)
├── output/            # Generated files (gitignored)
│   ├── script.json
│   ├── voice.mp3
│   ├── captions.srt
│   └── final.mp4
├── credentials.json   # Google OAuth credentials (gitignored)
├── token.pickle       # OAuth token cache (gitignored)
└── requirements.txt
```

## Notes
- All output files are gitignored; only source code is versioned
- Ollama runs locally - no API costs, complete privacy
- Edge TTS is free - no API keys needed
- FFmpeg is required for video rendering
- Background videos must be added manually to `assets/backgrounds/`
- YouTube API requires OAuth2 authentication (one-time browser authorization)
- Token is cached in `token.pickle` for subsequent uploads

## Troubleshooting

### FFmpeg not found
```bash
brew install ffmpeg
```

### No background videos
Add `.mp4` files to `assets/backgrounds/` directory

### Ollama connection errors
Ensure Ollama is running: `ollama serve`

### Missing output files
Run scripts in order: agent.py → tts.py → captions.py → render.py

### YouTube API authentication errors
- Ensure `credentials.json` is in project root
- Delete `token.pickle` and re-run to re-authenticate
- Check that YouTube Data API v3 is enabled in Google Cloud Console

### YouTube upload fails
- Verify video file exists: `output/final.mp4`
- Check that script.json exists with title and description
- Ensure OAuth token is valid (delete token.pickle to refresh)
- For scheduled uploads, ensure SCHEDULE_HOURS is set correctly
