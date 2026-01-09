#!/usr/bin/env python3
"""
Generate 100% original 'reddit-vibes' short scripts using the OpenAI API
and save them to output/script.json. Phase 1 only: no Reddit, no upload, no TTS.
"""

import os
import random
import json
from dotenv import load_dotenv
from openai import OpenAI

# Load environment
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHANNEL_STYLE = os.getenv("CHANNEL_STYLE", "reddit_vibes")
NICHE = os.getenv("NICHE", "aita").lower()

if not OPENAI_API_KEY:
    raise SystemExit("Missing OPENAI_API_KEY in your .env. Copy .env.example to .env and set your key.")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "script.json")

# Themes per niche to add variety
THEMES = {
    "aita": [
        "family drama over inheritance",
        "wedding argument about etiquette",
        "roommate conflict over chores and money",
    ],
    "confession": [
        "admitting a long-hidden secret",
        "confession about a mistake at work",
        "guilt over a past relationship choice",
    ],
    "relationships": [
        "miscommunication leads to breakup fears",
        "dating boundary issues",
        "surprising support from an ex"
    ],
    "creepy": [
        "strange neighbor behavior",
        "late-night knocks with no one there",
        "unsettling discovery in the attic"
    ],
}

# Choose a theme list based on NICHE
theme_list = THEMES.get(NICHE, THEMES["aita"])


def build_prompt(theme):
    """Create a system and user prompt that forces original, reddit-vibe output in strict JSON."""
    system = (
        "You are a creative assistant that writes short, engaging, original stories with a 'Reddit-like' voice but DO NOT copy or quote any real Reddit content. "
        "Output ONLY valid JSON with the schema: {\n  \"title\": \"\",\n  \"description\": \"\",\n  \"script\": \"\"\n}." 
    )

    user = (
        "Write a brief, original story inspired by the 'Reddit vibes' for the following theme. Do NOT quote or reference any real Reddit posts, usernames, or private details. Keep it suitable for a YouTube Shorts narration: 30–40 seconds (about 90–130 words). Start with a hook, end with a question, avoid explicit sexual content and graphic violence. Return ONLY the JSON object (no extra text).\n\n"
        f"Theme: {theme}\n\n"
        "Be creative, concise, and make sure the JSON parses correctly."
    )

    return system, user


def call_openai(system_prompt, user_prompt):
    """Call OpenAI using the modern client and return the assistant content."""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.9,
        max_tokens=500,
    )
    return resp.choices[0].message.content


def extract_json(text):
    """Extract the first JSON object found in text (handles markdown backticks)."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model output")
    return text[start : end + 1]


def save_output(data_obj):
    """Ensure output dir exists, append #shorts to description, and save pretty JSON."""
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    # Ensure description contains #shorts
    if "description" in data_obj and "#shorts" not in data_obj["description"]:
        data_obj["description"] = data_obj["description"].strip() + "\n\n#shorts"
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data_obj, f, ensure_ascii=False, indent=2)
    return OUTPUT_PATH


def main():
    theme = random.choice(theme_list)
    print(f"Generating original reddit-vibes story for theme: {theme}")

    system_prompt, user_prompt = build_prompt(theme)
    raw = call_openai(system_prompt, user_prompt)

    try:
        json_text = extract_json(raw)
        data = json.loads(json_text)
    except Exception as e:
        print("Failed to parse JSON from model output:", e)
        print("Raw output:\n", raw)
        return

    # Validate keys
    for k in ("title", "description", "script"):
        if k not in data or not isinstance(data[k], str) or not data[k].strip():
            print(f"Model output missing or invalid '{k}'")
            print("Raw output:\n", raw)
            return

    out_path = save_output(data)
    print(f"Saved generated script to {out_path}")
    print("Preview:\n")
    print("Title:", data["title"])
    print("Description:\n", data["description"])
    print("Script:\n", data["script"])


if __name__ == "__main__":
    main()
