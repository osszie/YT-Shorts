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
        # Ask Ollama to enforce valid JSON output (dramatically reduces "```json" + invalid JSON issues).
        # Supported by Ollama's /api/generate.
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.9,
            # Give the model enough room to finish valid JSON + a full script.
            "num_predict": 500,
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

    names = ["Alex", "Jordan", "Sam", "Taylor", "Casey", "Riley", "Morgan", "Jamie"]
    a, b = random.sample(names, 2)
    detail_bits = [
        "a screenshot that contradicted what they told everyone",
        "a receipt with the date/time that didn’t line up",
        "a group chat message they 'forgot' to mention",
        "a voicemail that changed the whole story",
        "a calendar invite that proved who agreed to what",
    ]
    escalation_bits = [
        "then they posted a vague story online and people started DM’ing me",
        "then they told our friends I was being 'dramatic' before we even talked",
        "then they changed the agreement like it never existed",
        "then they tried to make it about my tone instead of the actual issue",
    ]
    proof = random.choice(detail_bits)
    escalation = random.choice(escalation_bits)

    # ~120–170 words with concrete details (more variety, less same-y)
    body = (
        f"For context, it started with {theme}. "
        f"{a} and I were fine until {b} stepped in and suddenly the story changed depending on who was in the room. "
        "At first I tried to keep it calm and handle it privately, but it kept getting framed like I was the problem. "
        f"Then I found {proof}. "
        f"When I brought it up, {b} acted like I was 'attacking' them and said I was controlling. "
        f"{escalation}. "
        "Now the group chat is split into two teams, and I’m getting blamed for 'starting drama' even though I only responded to what was already being said. "
        f"{cta}"
    )

    script = "\n".join([hook, tease, body])
    return {
        "title": f"Reddit Story: {theme.title()}",
        "description": f"A Reddit-style story about {theme}. #shorts",
        "script": script,
    }


def _word_count(s: str) -> int:
    return len(re.findall(r"\S+", s or ""))


def _split_sentences(text: str) -> list[str]:
    # Lightweight sentence splitter good enough for short scripts
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if p and p.strip()]


def normalize_script(script: str, theme: str) -> str:
    """
    Make sure the script always has:
    - Line 1: hook
    - Line 2: tease
    - Line 3+: body ending with a CTA question
    This prevents "same script" fallback and makes weak model outputs usable.
    """
    hook_templates = [
        "Stop scrolling—this is actually insane.",
        "I thought this was a small issue… until it blew up.",
        "This comment section would tear you apart.",
        "I didn’t expect one rule to start a war.",
    ]
    tease_templates = [
        "Wait for the last comment.",
        "Wait until you hear what they said at the end.",
        "Wait for the twist—seriously.",
        "Wait for the DM I got after this.",
    ]
    cta_templates = [
        "Who’s wrong—me or them?",
        "Team A or Team B?",
        "Am I overreacting, or is this messed up?",
        "What would you do?",
    ]

    raw = (script or "").strip()
    # Strip common label formats the model sometimes inserts
    raw = re.sub(r"^\s*(\[hook\]|\[tease\]|\[story\]|hook:|tease:)\s*", "", raw, flags=re.I | re.M)
    raw = raw.replace("\r\n", "\n")

    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if lines:
        hook = lines[0]
        # If the model already provided a "wait..." style tease on the next line, keep it.
        if len(lines) > 1 and re.search(r"\bwait\b", lines[1], flags=re.I):
            tease = lines[1]
            body = " ".join(lines[2:]) if len(lines) > 2 else ""
        else:
            tease = random.choice(tease_templates)
            body = " ".join(lines[1:])
    else:
        sentences = _split_sentences(raw)
        if sentences:
            hook = sentences[0]
            body = " ".join(sentences[1:]) if len(sentences) > 1 else ""
        else:
            hook = random.choice(hook_templates)
            body = ""
        tease = random.choice(tease_templates)

    # If hook is too long, shorten it
    if len(hook) > 90:
        hook = hook[:87].rstrip() + "..."

    # Ensure body has enough substance
    if _word_count(body) < 80:
        pad = (
            f"For context, it started with {theme}. "
            "At first it sounded harmless, but the details kept changing depending on who was listening. "
            "Then someone posted about it like I was the villain, and the group chat exploded."
        )
        body = (body + " " + pad).strip()

    # Ensure ending CTA question
    if not body.endswith("?"):
        body = body.rstrip()
        # If it already ends in punctuation, just add CTA. Otherwise add a question mark CTA.
        body = body + " " + random.choice(cta_templates)
        if not body.endswith("?"):
            body = body.rstrip(".! ") + "?"

    return "\n".join([hook, tease, body]).strip()


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
            # Normalize weak model outputs into the required hook/tease/body format.
            obj["script"] = normalize_script(obj["script"], theme)

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
