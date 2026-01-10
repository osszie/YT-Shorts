#!/usr/bin/env python3
"""
Generate 100% original 'reddit-vibes' short scripts using Hugging Face Inference API
and save them to output/script.json. Phase 1 only: no Reddit, no upload, no TTS.
"""

import os
import random
import json
import time
import pathlib
from dotenv import load_dotenv
import requests

# Load .env from project root deterministically
load_dotenv(dotenv_path=str(pathlib.Path(__file__).resolve().parents[1] / '.env'))

HF_API_TOKEN = os.getenv('HF_API_TOKEN')
MODEL_ID = os.getenv('MODEL_ID', 'mistralai/Mistral-7B-Instruct-v0.2')
NICHE = os.getenv('NICHE', 'aita').lower()

if not HF_API_TOKEN:
    raise SystemExit('Missing HF_API_TOKEN in .env. Create an access token on Hugging Face and add it to .env')

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output', 'script.json')

# Themes per niche
THEMES = {
    'aita': [
        'family drama over inheritance',
        'wedding argument about etiquette',
        'roommate conflict over chores and money',
    ],
    'confession': [
        'admitting a long-hidden secret',
        'confession about a mistake at work',
        'guilt over a past relationship choice',
    ],
    'relationships': [
        'miscommunication leads to breakup fears',
        'dating boundary issues',
        'surprising support from an ex',
    ],
    'creepy': [
        'strange neighbor behavior',
        'late-night knocks with no one there',
        'unsettling discovery in the attic',
    ],
}

theme_list = THEMES.get(NICHE, THEMES['aita'])


def build_prompt(theme):
    prompt = (
        'You are a creative assistant. Produce a 100% ORIGINAL short story that captures "Reddit-vibes" for the theme below. Do NOT copy or quote any real Reddit content or usernames.\n\n'
        'Constraints:\n'
        '- 90–130 words (30–40 seconds spoken)\n'
        '- Start with a strong hook (first sentence)\n'
        "- End with a question\n"
        '- Avoid explicit sexual content and graphic violence\n'
        '- Return ONLY a JSON object with this exact schema (no markdown, no backticks, no extra text):\n'
        '{\n'
        '  "title": "story title here",\n'
        '  "description": "brief description #shorts",\n'
        '  "script": "the full story script here"\n'
        '}\n\n'
        f'Theme: {theme}\n\n'
        'Write the story now.'
    )
    return prompt


def call_hf(prompt):
    url = f"https://api-inference.huggingface.co/models/{MODEL_ID}"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 300,
            "temperature": 0.9,
            "return_full_text": False
        }
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        # try to show helpful error
        try:
            err = resp.json()
        except Exception:
            resp.raise_for_status()
        if isinstance(err, dict) and 'error' in err:
            raise RuntimeError(f"Hugging Face API error: {err['error']}")
        else:
            resp.raise_for_status()
    data = resp.json()
    # HF may return a list of {'generated_text': ...}
    if isinstance(data, list) and len(data) and 'generated_text' in data[0]:
        return data[0]['generated_text']
    # Or a dict with 'generated_text'
    if isinstance(data, dict) and 'generated_text' in data:
        return data['generated_text']
    # Unexpected format
    raise RuntimeError(f"Unexpected HF response format: {data}")


def extract_json(text):
    # Try direct parse first
    try:
        return json.loads(text)
    except Exception:
        # Fallback: locate first {...}
        start = text.find('{')
        end = text.rfind('}')
        if start == -1 or end == -1:
            raise ValueError('No JSON found in model output')
        substring = text[start:end+1]
        return json.loads(substring)


def save_output(obj):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    # ensure description contains #shorts
    if 'description' in obj and '#shorts' not in obj['description']:
        obj['description'] = obj['description'].strip() + '\n\n#shorts'
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return OUTPUT_PATH


def main():
    theme = random.choice(theme_list)
    print('Theme:', theme)
    prompt = build_prompt(theme)

    # One retry: if parsing fails, try again with a stricter instruction
    for attempt in range(2):
        if attempt == 1:
            print('Retrying with stricter JSON-only instruction...')
            prompt = 'IMPORTANT: Return ONLY valid JSON, no markdown, no backticks, no explanations. JSON schema: {"title": "...", "description": "...", "script": "..."}\n\n' + prompt
            time.sleep(1)
        try:
            raw = call_hf(prompt)
        except Exception as e:
            print('Hugging Face API call failed:', e)
            return

        try:
            obj = extract_json(raw)
        except Exception as e:
            print('Failed to parse JSON from model output:', e)
            print('Model output was:\n', raw)
            continue

        # Validate
        for k in ('title', 'description', 'script'):
            if k not in obj or not isinstance(obj[k], str) or not obj[k].strip():
                print(f"Output missing or invalid '{k}'")
                print('Model output was:\n', raw)
                break
        else:
            out_path = save_output(obj)
            print('Saved generated script to', out_path)
            print('\nPreview:\n')
            print('Title:', obj['title'])
            print('Description:\n', obj['description'])
            print('Script:\n', obj['script'])
            return

    print('Failed to generate valid JSON after retries.')


if __name__ == '__main__':
    main()
