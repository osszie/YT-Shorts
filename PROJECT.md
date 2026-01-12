# yt-shorts-agent - Project Vision

## Overall Goal
Automate the creation of YouTube Shorts content using AI-generated Reddit-style stories, complete with voice narration and video editing.

## Why Local Ollama?
We chose Ollama for Phase 1 because:
- **No API costs**: Run models locally, completely free
- **Privacy**: Your prompts and generated content never leave your machine
- **Reliability**: No dependency on external API availability or rate limits
- **Flexibility**: Easy to switch models or experiment with different ones
- **Performance**: Fast inference on modern hardware (especially Apple Silicon)

## Architecture Overview

### Phase 1: Story Generation ✅ COMPLETE
- **Status**: Working
- **Tech**: Ollama + phi3:mini
- **Output**: JSON files with title, description, and script
- **Location**: `output/script.json`

### Phase 2: Voice Synthesis ✅ COMPLETE
- Text-to-Speech conversion using Edge TTS
- Natural-sounding narration
- Multiple voice options
- Audio file generation

### Phase 3: Video Creation ✅ COMPLETE
- Background visuals (stock footage from assets/backgrounds/)
- Text overlays (burned-in captions)
- Audio synchronization
- Export to YouTube-ready format (1080x1920)

### Phase 4: YouTube Upload ✅ COMPLETE
- Automated upload via YouTube Data API v3
- Metadata management (title, description, tags from script.json)
- Scheduling support (delayed publishing)
- OAuth2 authentication with token persistence

## Current Tech Stack
- **Python 3.7+**: Core language
- **Ollama**: Local LLM inference
- **phi3:mini**: 3.8B parameter model (fast, efficient, good quality)
- **python-dotenv**: Environment variable management
- **requests**: HTTP client for Ollama API

## Future Considerations
- Model switching (support for larger models when needed)
- Batch generation
- Content quality filtering
- A/B testing different story styles
- Analytics and performance tracking
