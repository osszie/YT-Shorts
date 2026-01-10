# Daily Checklist

## Phase 1: Story Generation ✅ COMPLETE

### Setup (One-time)
- [x] Install Ollama
- [x] Pull phi3:mini model
- [x] Set up Python virtual environment
- [x] Install dependencies
- [x] Configure .env (optional)

### Daily Run
1. [ ] Ensure Ollama is running: `ollama serve` (or check if already running)
2. [ ] Activate virtual environment: `source .venv/bin/activate`
3. [ ] Run the agent: `python scripts/agent.py`
4. [ ] Review generated story in `output/script.json`
5. [ ] Verify story quality and uniqueness

### Troubleshooting
- If Ollama connection fails: Check that `ollama serve` is running
- If model not found: Run `ollama pull phi3:mini`
- If JSON parsing fails: The script will retry automatically with stricter prompts

## Phase 2: Voice Synthesis (Not Started)
- [ ] Research TTS options
- [ ] Implement voice generation
- [ ] Test audio quality
- [ ] Integrate with story generation

## Phase 3: Video Creation (Not Started)
- [ ] Research video editing libraries
- [ ] Implement video generation
- [ ] Test output quality
- [ ] Integrate with previous phases

## Phase 4: YouTube Upload (Not Started)
- [ ] Set up YouTube API credentials
- [ ] Implement upload functionality
- [ ] Test upload process
- [ ] Add scheduling features
