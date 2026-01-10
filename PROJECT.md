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

### Phase 2: Voice Synthesis (Planned)
- Text-to-Speech conversion
- Natural-sounding narration
- Multiple voice options
- Audio file generation

### Phase 3: Video Creation (Planned)
- Background visuals (stock footage or AI-generated)
- Text overlays
- Audio synchronization
- Export to YouTube-ready format

### Phase 4: YouTube Upload (Planned)
- Automated upload via YouTube API
- Metadata management
- Scheduling
- Analytics tracking

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
