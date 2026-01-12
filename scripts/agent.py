#!/usr/bin/env python3
"""
Generate 100% original 'reddit-vibes' short scripts using Ollama (local AI)
and save them to output/script.json. Phase 1 only: no Reddit, no upload, no TTS.
"""

import os
import random
import json
import time
import pathlib
import re
from dotenv import load_dotenv
import requests

# Load .env from project root deterministically
load_dotenv(dotenv_path=str(pathlib.Path(__file__).resolve().parents[1] / '.env'))

# Ollama configuration
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
MODEL_NAME = os.getenv('MODEL_NAME', 'phi3:mini')
NICHE = os.getenv('NICHE', 'aita').lower()

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
        '- 110–150 words (aim ~45–60 seconds spoken)\n'
        '- Must feel like a Reddit story (AITA / relationship / confession / creepy vibe)\n'
        '- HOOK REQUIREMENTS:\n'
        '  - First line: an immediate pattern-break hook (short, punchy, scroll-stopping)\n'
        '  - Second line: an open-loop tease (e.g., "Wait for the last comment.")\n'
        '  - Then the story unfolds quickly with concrete details\n'
        '- ENDING REQUIREMENTS:\n'
        '  - End with a strong CTA question for comments ("Who’s wrong?" / "Team A or Team B?" / "What would you do?")\n'
        '- Avoid explicit sexual content and graphic violence\n'
        '- Avoid long setup; get to conflict fast\n'
        '- "script" MUST be a single plain string (not an object). Do NOT use labels like [Hook] or [Tease].\n'
        '- Put hook + tease on their own lines at the very start of the script:\n'
        '  Line 1: HOOK.\n'
        '  Line 2: TEASE.\n'
        '  Line 3+: the story.\n'
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


def call_ollama(prompt):
    """Call Ollama API to generate text using the configured model."""
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.9,
            # Give the model enough room to finish valid JSON + a full script.
            "num_predict": 500,
            # Encourage the model to stop after finishing the JSON object.
            "stop": ["\n}\n", "\n}\r\n", "}\n```", "}\r\n```"],
        }
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        
        if 'response' in data:
            return data['response']
        else:
            raise RuntimeError(f"Unexpected Ollama response format: {data}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Ollama API error: {e}. Make sure Ollama is running (ollama serve) and the model '{MODEL_NAME}' is available (ollama pull {MODEL_NAME})")


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


def fallback_story(theme: str):
    """
    Deterministic fallback if Ollama fails to return valid JSON.
    Keeps the same hook + tease + CTA structure so the pipeline always works.
    """
    hook_templates = [
        "I thought my family was close… until this happened.",
        "I walked into my own home and realized I’d been lied to.",
        "I didn’t think a small rule could start a war… I was wrong.",
        "This is the pettiest argument I’ve ever seen—until the twist.",
    ]
    tease_templates = [
        "Wait for the last message—I still can’t believe it.",
        "Wait for what my sibling said at the end.",
        "Wait until you hear the final comment.",
        "Wait for the part that made everyone pick sides.",
    ]
    cta_templates = [
        "Am I overreacting here, or would you be mad too?",
        "Who’s wrong—me or them?",
        "Team me or Team them? What would you do?",
        "Was I out of line, or was this totally unfair?",
    ]
    hook = random.choice(hook_templates)
    tease = random.choice(tease_templates)
    cta = random.choice(cta_templates)

    # ~120–150 words with concrete details
    body = (
        f"For context, it started with {theme}. "
        "I tried to keep it calm, but every time we talked, someone would change the story. "
        "One person kept saying it was 'no big deal'… while also acting like they were the victim. "
        "Then I found proof—screenshots, receipts, and a timeline that didn’t match what they told everyone. "
        "When I brought it up, they flipped it on me and accused me of being controlling. "
        "Now the group chat is split, people are picking sides, and I’m getting blamed for 'making it public' even though they started spreading it first. "
        f"{cta}"
    )

    script = "\n".join([hook, tease, body])
    return {
        "title": "Reddit Story: Pick a Side",
        "description": f"A Reddit-style story about {theme}. #shorts",
        "script": script,
    }


def _word_count(s: str) -> int:
    return len(re.findall(r"\S+", s or ""))


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
            raw = call_ollama(prompt)
        except Exception as e:
            print('Ollama API call failed:', e)
            return

        try:
            obj = extract_json(raw)
        except Exception as e:
            print('Failed to parse JSON from model output:', e)
            print('Model output was:\n', raw)
            continue

        # Validate
        for k in ('title', 'description', 'script'):
            if k not in obj:
                print(f"Output missing '{k}'")
                print('Model output was:\n', raw)
                break

            # Some models mistakenly return script as an object; reject so we retry.
            if k == 'script' and not isinstance(obj[k], str):
                print("Output has invalid 'script' (must be a string, not an object).")
                print('Model output was:\n', raw)
                break

            if not isinstance(obj[k], str) or not obj[k].strip():
                print(f"Output missing or invalid '{k}'")
                print('Model output was:\n', raw)
                break
        else:
            # Enforce word count target to keep shorts length consistent
            wc = _word_count(obj["script"])
            if wc < 105 or wc > 170:
                print(f"Script length out of range ({wc} words). Retrying...")
                continue

            # Enforce hook+tease lines (first two lines) without bracket labels
            lines = [ln.strip() for ln in obj["script"].splitlines() if ln.strip()]
            if len(lines) < 3:
                print("Script format invalid (needs hook line, tease line, then story). Retrying...")
                continue
            if any(lines[0].startswith(x) for x in ("[", "hook:", "tease:")) or any(lines[1].startswith(x) for x in ("[", "hook:", "tease:")):
                print("Script uses labels for hook/tease; retrying...")
                continue

            out_path = save_output(obj)
            print('Saved generated script to', out_path)
            print('\nPreview:\n')
            print('Title:', obj['title'])
            print('Description:\n', obj['description'])
            print('Script:\n', obj['script'])
            return

    print('Failed to generate valid JSON after retries. Using fallback template script.')
    obj = fallback_story(theme)
    out_path = save_output(obj)
    print('Saved fallback script to', out_path)
    print('\nPreview:\n')
    print('Title:', obj['title'])
    print('Description:\n', obj['description'])
    print('Script:\n', obj['script'])


if __name__ == '__main__':
    main()
