# yt-shorts-agent - Project Status Summary

## Project Overview
Automated YouTube Shorts content generation pipeline using local AI. The project generates original Reddit-style stories, converts them to voice narration, and is designed to eventually create full video content with automated YouTube uploads.

## Current Status: Phase 1, 2, 3, & 4 Complete ✅

### Phase 1: Story Generation (COMPLETE)
**Technology Stack:**
- **Ollama** (local AI inference engine)
- **phi3:mini** model (3.8B parameters, Microsoft)
- **Python 3.7+**

**What It Does:**
- Generates 100% original Reddit-style stories (AITA/confession/relationships/creepy niches)
- Stories are 90-130 words (30-40 seconds when spoken)
- Outputs JSON format with title, description, and script
- No API costs - runs completely locally
- Models stored on external SSD to save internal disk space

**Key Files:**
- `scripts/agent.py` - Main story generation script
- `output/script.json` - Generated story output (gitignored)

**How It Works:**
1. Picks random theme based on NICHE setting (aita, confession, relationships, creepy)
2. Builds prompt with constraints (hook, question ending, no explicit content)
3. Calls Ollama API locally to generate story
4. Extracts JSON from model output (with retry logic for parsing)
5. Validates and saves to `output/script.json`

**Configuration:**
- Environment variables: `OLLAMA_BASE_URL`, `MODEL_NAME`, `NICHE`
- Defaults: `http://localhost:11434`, `phi3:mini`, `aita`

**Run Command:**
```bash
python scripts/agent.py
```

---

### Phase 2: Voice Synthesis (COMPLETE)
**Technology Stack:**
- **Edge TTS** (Microsoft's free text-to-speech)
- **Python asyncio** for async TTS generation

**What It Does:**
- Reads `output/script.json` 
- Extracts the "script" field
- Generates MP3 audio file using Microsoft Edge TTS
- Saves to `output/voice.mp3`
- Configurable voice, rate, and pitch

**Key Files:**
- `scripts/tts.py` - TTS generation script
- `output/voice.mp3` - Generated audio output (gitignored)

**How It Works:**
1. Checks if `output/script.json` exists (exits if missing)
2. Loads JSON and extracts script text
3. Uses Edge TTS to generate speech with configured voice settings
4. Saves MP3 file to output directory
5. Prints success message with voice settings used

**Configuration:**
- Environment variables: `TTS_VOICE`, `TTS_RATE`, `TTS_PITCH`
- Defaults: `en-US-GuyNeural`, `+5%`, `+0Hz`

**Run Command:**
```bash
python scripts/tts.py
```

---

## Current Workflow
1. **Generate Story**: `python scripts/agent.py` → creates `output/script.json`
2. **Generate Voice**: `python scripts/tts.py` → creates `output/voice.mp3`
3. **Generate Captions**: `python scripts/captions_bounce.py` → creates `output/captions.ass` (word-level animated)
4. **Render Video**: `python scripts/render.py` → creates `output/final.mp4`
5. **Upload to YouTube**: `python scripts/upload_youtube.py` → validates + dry-run support + upload to YouTube

Recommended: run everything with `python scripts/run_all.py` (optionally `--upload`).

All scripts work independently and can be run in sequence.

---

## Project Structure
```
yt-shorts-agent/
├── scripts/
│   ├── agent.py          # Phase 1: Story generation (Ollama)
│   ├── tts.py            # Phase 2: Voice synthesis (Edge TTS)
│   ├── captions_bounce.py# Phase 3a: Word-level animated captions (ASS)
│   ├── render.py         # Phase 3b: Video rendering
│   ├── upload_youtube.py # Phase 4: YouTube upload agent (dry-run support)
│   └── run_all.py        # Orchestrator: phases 1–4
├── assets/
│   └── backgrounds/      # Background video files (.mp4)
├── output/               # Generated files (gitignored)
│   ├── script.json       # Story output
│   ├── voice.mp3         # Audio output
│   ├── captions.ass      # Subtitle file (ASS)
│   └── final.mp4         # Final video
├── credentials.json      # Google OAuth credentials (gitignored)
├── token.pickle          # OAuth token cache (gitignored)
├── .env                  # Environment variables (gitignored)
├── .env.example          # Example env file
├── requirements.txt      # Python dependencies
├── README.md             # Setup and usage instructions
├── PROJECT.md            # Project vision and architecture
├── DAILY_CHECKLIST.md    # Daily workflow checklist
└── .gitignore           # Ignores output/, .env, .venv/, etc.
```

---

## Dependencies
- `python-dotenv` - Environment variable management
- `requests` - HTTP client for Ollama API
- `edge-tts` - Microsoft Edge TTS library
- `aiohttp` - Async HTTP (dependency of edge-tts)
- `google-api-python-client` - YouTube Data API v3 client
- `google-auth-httplib2` - HTTP transport for Google auth
- `google-auth-oauthlib` - OAuth2 authentication for Google APIs

---

### Phase 3: Video Creation (COMPLETE)
**Technology Stack:**
- **FFmpeg** for video processing
- **Python** for caption timing and rendering orchestration

**What It Does:**
- Generates timed SRT captions from script and audio
- Renders 1080x1920 vertical video (YouTube Shorts format)
- Combines background video, voice audio, and burned-in captions
- Outputs final.mp4 ready for YouTube upload

**Key Files:**
- `scripts/captions_bounce.py` - Word-level animated captions (ASS)
- `scripts/render.py` - Video rendering with FFmpeg
- `output/captions.ass` - Timed subtitle file (ASS)
- `output/final.mp4` - Final video output

**How It Works:**
1. Captions script analyzes audio and script to create timed subtitles
2. Render script selects random background video from assets/backgrounds/
3. FFmpeg combines background, audio, and captions into final video
4. Video is cropped/scaled to 1080x1920 (9:16 aspect ratio)

**Configuration:**
- Background videos must be added to `assets/backgrounds/`
- Videos are randomly selected for each render

**Run Commands:**
```bash
python scripts/captions_bounce.py
python scripts/render.py
```

---

### Phase 4: YouTube Upload (COMPLETE)
**Technology Stack:**
- **Google YouTube Data API v3**
- **OAuth2** for authentication
- **Python google-api-python-client**

**What It Does:**
- Uploads final.mp4 to YouTube automatically
- Uses metadata from script.json (title, description)
- Supports scheduled uploads (delayed publishing)
- Configurable privacy settings (private, unlisted, public)
- Tag management and category selection

**Key Files:**
- `scripts/upload_youtube.py` - YouTube upload agent (validation + dry-run)
- `credentials.json` - Google OAuth credentials (user-provided)
- `token.pickle` - Cached OAuth token for subsequent uploads

**How It Works:**
1. Loads metadata from `output/script.json`
2. Authenticates with YouTube API using OAuth2
3. Uploads `output/final.mp4` with metadata
4. Supports scheduling via `SCHEDULE_HOURS` environment variable
5. Returns YouTube video ID and URL

**Configuration:**
- Environment variables: `YOUTUBE_CATEGORY_ID`, `YOUTUBE_PRIVACY`, `YOUTUBE_TAGS`, `SCHEDULE_HOURS`
- Defaults: Category 22 (People & Blogs), private, tags from env, immediate upload
- Requires `credentials.json` from Google Cloud Console

**Setup Required:**
1. Create Google Cloud Project
2. Enable YouTube Data API v3
3. Create OAuth 2.0 credentials (Desktop app)
4. Download and save as `credentials.json` in project root
5. First run will open browser for authorization

**Run Command:**
```bash
python scripts/upload_youtube.py
```

---

## What's NOT Implemented Yet

### Analytics Tracking (FUTURE)
- Video performance metrics
- View count tracking
- Engagement analytics
- Automated reporting

---

## Key Design Decisions

1. **Local AI (Ollama)**: Chosen for zero API costs, privacy, and reliability
2. **Free TTS (Edge TTS)**: Microsoft's free TTS service, no API keys needed
3. **Modular Scripts**: Each phase is a separate script for flexibility
4. **Gitignored Output**: Generated files stay local, only code is versioned
5. **Environment Variables**: All configuration via .env for flexibility

---

## Technical Details

**Ollama Setup:**
- Models stored on external SSD: `/Volumes/External Drive/ollama`
- Symlink from `~/.ollama/models` to external drive
- Environment variable: `OLLAMA_MODELS` set in `~/.zshrc`

**Edge TTS:**
- No API keys required
- Free Microsoft service
- Multiple voice options available
- Configurable rate and pitch

**Error Handling:**
- Agent retries JSON parsing with stricter prompts
- TTS checks for required files before running
- Clear error messages for troubleshooting

---

## Repository
- **GitHub**: https://github.com/osszie/YT-Shorts.git
- **Branch**: `main` (up to date)
- **Latest Commit**: "Phase 2: add Edge TTS voice generation"

---

## Next Steps (For ChatGPT Planning)
The project needs guidance on:
1. **Phase 3 Implementation**: Best approach for video generation (FFmpeg? MoviePy? Other?)
2. **Phase 4 Implementation**: YouTube API setup and upload automation
3. **Optimization**: Any improvements to current Phases 1 & 2
4. **Architecture**: Should scripts be combined? Add a main orchestrator?
5. **Error Handling**: Enhance robustness and user experience
6. **Testing**: Add tests for each phase
7. **Documentation**: Any additional docs needed

---

## Current Limitations
- Manual workflow (run scripts separately - could be orchestrated)
- No batch processing
- No content quality filtering
- No analytics tracking/automated reporting
- YouTube scheduling requires manual calculation (hours from now)

---

## Environment Setup Required
1. Ollama installed and running (`ollama serve`)
2. phi3:mini model pulled (`ollama pull phi3:mini`)
3. Python virtual environment with dependencies installed
4. `.env` file configured (optional, defaults work)

---

This project is a complete automation pipeline for YouTube Shorts content creation, currently at 100% completion (4 of 4 phases done). All core functionality is implemented and working.
