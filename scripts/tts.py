#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import edge_tts

ROOT = os.path.dirname(os.path.dirname(__file__))
SCRIPT_JSON = os.path.join(ROOT, "output", "script.json")
OUT_MP3 = os.path.join(ROOT, "output", "voice.mp3")

VOICE = os.getenv("TTS_VOICE", "en-US-GuyNeural")
RATE = os.getenv("TTS_RATE", "+5%")
PITCH = os.getenv("TTS_PITCH", "+0Hz")

async def main():
    if not os.path.exists(SCRIPT_JSON):
        print("❌ Missing output/script.json. Run: python scripts/agent.py first.")
        sys.exit(1)

    with open(SCRIPT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    text = (data.get("script") or "").strip()
    if not text:
        print("❌ output/script.json is missing the 'script' field.")
        sys.exit(1)

    os.makedirs(os.path.dirname(OUT_MP3), exist_ok=True)

    communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
    await communicate.save(OUT_MP3)

    print(f"✅ Saved voice to: {OUT_MP3}")
    print(f"Voice: {VOICE} | Rate: {RATE} | Pitch: {PITCH}")

if __name__ == "__main__":
    asyncio.run(main())
