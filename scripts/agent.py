#!/usr/bin/env python3
"""
Generate 100% original 'reddit-vibes' short scripts using Google Gemini API
and save them to output/script.json. Phase 1 only: no Reddit, no upload, no TTS.
"""

import os
import random
import json
import time
import pathlib
import re
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import RequestOptions

# Load .env from project root deterministically
load_dotenv(dotenv_path=str(pathlib.Path(__file__).resolve().parents[1] / '.env'))

# Gemini API configuration
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is required. Set it in your .env file.")

# Configure Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

# Model configuration
MODEL_NAME = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')  # Options: gemini-2.0-flash, gemini-2.5-flash, gemini-2.5-pro
NICHE = os.getenv('NICHE', 'aita').lower()

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output', 'script.json')

# Themes per niche - expanded for more variety
THEMES = {
    'aita': [
        'family drama over inheritance',
        'wedding argument about etiquette',
        'roommate conflict over chores and money',
        'parenting disagreement at family gathering',
        'friend group split over vacation planning',
        'sibling rivalry over shared space',
        'in-law conflict about holiday traditions',
        'work friend boundary crossing',
        'neighbor dispute about property line',
        'group chat drama over event planning',
        'friend borrowing money without asking',
        'family member using my photos without permission',
        'colleague taking credit for my work',
        'friend group excluding someone unfairly',
        'family member making decisions without consulting me',
    ],
    'confession': [
        'admitting a long-hidden secret',
        'confession about a mistake at work',
        'guilt over a past relationship choice',
        'secret I kept from my best friend',
        'confession about lying to my family',
        'guilt over not speaking up when I should have',
        'secret hobby I never told anyone about',
        'confession about a financial mistake',
        'guilt over cutting someone off without explanation',
        'secret about my past that could change everything',
        'confession about pretending to be someone I\'m not',
        'guilt over a decision that hurt someone',
        'secret relationship I kept hidden',
        'confession about breaking a promise',
        'guilt over not being there when someone needed me',
    ],
    'relationships': [
        'miscommunication leads to breakup fears',
        'dating boundary issues',
        'surprising support from an ex',
        'partner\'s friend causing tension',
        'long-distance relationship struggle',
        'meeting partner\'s family for the first time',
        'relationship moving too fast or too slow',
        'partner\'s past coming back to haunt us',
        'friendship turning into something more',
        'partner keeping secrets about their past',
        'relationship tested by external pressure',
        'partner\'s behavior changing suddenly',
        'friendship ending over a misunderstanding',
        'dating someone my friends don\'t approve of',
        'relationship milestone causing unexpected conflict',
    ],
    'creepy': [
        'strange neighbor behavior',
        'late-night knocks with no one there',
        'unsettling discovery in the attic',
        'someone following me home',
        'strange messages from unknown number',
        'finding something that shouldn\'t be there',
        'neighbor watching me through windows',
        'strange sounds coming from next door',
        'package delivered I never ordered',
        'someone breaking into my car repeatedly',
        'strange person showing up at my door',
        'finding hidden cameras in my space',
        'neighbor leaving strange gifts',
        'someone knowing things they shouldn\'t know',
        'strange events happening at the same time every night',
        'hearing my name whispered when I\'m alone',
        'finding footprints outside my window after it rained',
        'receiving photos of myself I never took',
        'my security camera showing someone entering while I was home',
        'finding my things moved when I return home',
        'someone calling my name from outside at 3 AM',
        'discovering someone has been in my apartment',
        'receiving texts from my own number',
        'hearing someone walking in my hallway when I live alone',
        'finding a note in my handwriting I don\'t remember writing',
        'waking up to find my front door unlocked',
        'seeing the same person watching me from different locations',
        'receiving packages with items I searched for online',
        'hearing someone trying my door handle every night',
        'finding my car door open when I know I locked it',
    ],
}

theme_list = THEMES.get(NICHE, THEMES['aita'])

# YouTube SEO keywords and trending terms
SEO_KEYWORDS = {
    'aita': ['reddit stories', 'aita', 'am i the asshole', 'family drama', 'relationship advice', 'drama', 'tea', 'storytime', 'reddit', 'conflict'],
    'confession': ['reddit stories', 'confession', 'secret', 'storytime', 'guilt', 'reddit', 'honest', 'truth', 'reveal'],
    'relationships': ['relationship advice', 'dating', 'reddit stories', 'relationship drama', 'storytime', 'dating advice', 'reddit', 'love', 'breakup'],
    'creepy': ['reddit stories', 'creepy', 'scary', 'true story', 'storytime', 'reddit', 'mystery', 'unsettling', 'weird', 'truecrime', 'horror', 'paranormal', 'scary stories', 'creepy encounters'],
}

# Trending hashtags for YouTube Shorts
TRENDING_HASHTAGS = [
    '#shorts', '#reddit', '#redditstories', '#storytime', '#aita', '#drama', '#story', 
    '#viral', '#fyp', '#foryou', '#trending', '#tea', '#relationshipadvice', '#confession',
    '#reallife', '#truecrime', '#mystery', '#scary', '#creepy', '#familydrama'
]


def optimize_title_for_seo(title: str, theme: str, niche: str) -> str:
    """
    Optimize title for YouTube SEO:
    - Add trending keywords
    - Include emotional triggers
    - Add numbers when relevant
    - Keep under 60 chars for better mobile display
    - Make it clickable and engaging
    """
    title = title.strip()
    
    # Extract keywords based on niche
    keywords = SEO_KEYWORDS.get(niche, SEO_KEYWORDS['aita'])
    
    # Title optimization patterns
    patterns = [
        f"{title} | Reddit Stories",
        f"{title} - Storytime",
        f"Reddit: {title}",
        f"{title} (AITA?)",
        f"This {title.lower()}",
        f"{title} - You Won't Believe This",
    ]
    
    # If title is too generic, enhance it
    if len(title) < 30 or not any(kw in title.lower() for kw in ['reddit', 'story', 'drama', 'confession', 'secret']):
        # Add a keyword naturally
        if 'reddit' not in title.lower():
            title = f"{title} | Reddit Story"
    
    # Ensure it's engaging and clickable
    # Add emotional triggers
    emotional_triggers = ['This', 'I Can\'t Believe', 'Wait Until', 'You Won\'t Believe', 'This Is Wild']
    if not any(trigger.lower() in title.lower() for trigger in emotional_triggers):
        # Don't always add, but sometimes enhance
        if random.random() < 0.3:  # 30% chance
            trigger = random.choice(emotional_triggers)
            if not title.startswith(trigger):
                title = f"{trigger} {title}"
    
    # Keep under 60 chars for mobile (YouTube truncates at ~60)
    if len(title) > 60:
        # Try to shorten while keeping keywords
        words = title.split()
        shortened = []
        char_count = 0
        for word in words:
            if char_count + len(word) + 1 <= 57:  # Leave room for "..."
                shortened.append(word)
                char_count += len(word) + 1
            else:
                break
        title = " ".join(shortened)
        if len(title) < len(" ".join(words)):
            title += "..."
    
    return title


def optimize_description_for_seo(description: str, title: str, theme: str, niche: str) -> str:
    """
    Optimize description for YouTube SEO:
    - Add relevant hashtags
    - Include keywords
    - Add call-to-action
    - Keep engaging and searchable
    """
    desc = description.strip()
    
    # Remove existing #shorts if present (we'll add it back with other hashtags)
    desc = re.sub(r'\s*#shorts\s*', '', desc, flags=re.I).strip()
    
    # Add niche-specific hashtags
    niche_hashtags = {
        'aita': ['#aita', '#redditstories', '#storytime', '#drama', '#familydrama', '#relationshipadvice'],
        'confession': ['#confession', '#redditstories', '#storytime', '#secret', '#truth'],
        'relationships': ['#relationshipadvice', '#dating', '#redditstories', '#storytime', '#love'],
        'creepy': ['#creepy', '#scary', '#redditstories', '#storytime', '#mystery', '#truestory', '#truecrime', '#horror', '#paranormal', '#scarystories', '#creepyencounters'],
    }
    
    hashtags = niche_hashtags.get(niche, niche_hashtags['aita'])
    
    # Add 3-5 relevant hashtags (YouTube allows up to 15, but 5-8 is optimal)
    # Always include #shorts first (required for Shorts)
    selected_hashtags = ['#shorts']
    selected_hashtags.extend(random.sample(hashtags, min(3, len(hashtags))))
    # Add trending hashtags (excluding #shorts which we already have)
    remaining_trending = [h for h in TRENDING_HASHTAGS if h != '#shorts' and h not in selected_hashtags]
    selected_hashtags.extend(random.sample(remaining_trending, min(3, 8 - len(selected_hashtags))))
    
    hashtag_line = ' '.join(selected_hashtags)
    
    # Add call-to-action
    ctas = [
        'What do you think? Comment below! 👇',
        'Drop your thoughts in the comments! 💬',
        'Who do you agree with? Let me know! 👇',
        'What would you do? Comment below! 💭',
    ]
    cta = random.choice(ctas)
    
    # Build final description
    final_desc = f"{desc}\n\n{hashtag_line}\n\n{cta}"
    
    return final_desc


def build_prompt(theme):
    # Add variety with different hook styles - creepy-specific hooks for creepy niche
    if NICHE == 'creepy':
        hook_examples = [
            "I woke up at 3:17 AM to the sound of someone trying my door handle.",
            "I thought I was alone in my apartment until I heard footsteps in the hallway.",
            "I found a photo of myself sleeping on my phone that I never took.",
            "Someone has been leaving notes in my apartment, and I live alone.",
            "I keep hearing my name whispered when there's no one else around.",
            "My security camera caught someone entering my home while I was sleeping.",
            "I found footprints outside my window this morning, but it didn't rain last night.",
            "I received a text from my own number that I didn't send.",
        ]
        tease_examples = [
            "But what I found next made my blood run cold.",
            "Wait until you hear what the security footage showed.",
            "The twist at the end will make you check your locks.",
            "What happened next is something I still can't explain.",
            "But then I discovered something that changed everything.",
            "Wait for the part that made me call the police.",
            "The final detail is what really terrified me.",
        ]
    else:
        hook_examples = [
            "I thought I knew my family until last night.",
            "This started as a small misunderstanding and exploded into something I never saw coming.",
            "I'm sitting here at 3 AM wondering if I'm the problem or if everyone else is gaslighting me.",
            "I never thought a group chat could destroy a friendship, but here we are.",
            "My roommate did something that made me question everything I thought I knew about them.",
        ]
        tease_examples = [
            "Wait until you hear what happened next.",
            "The last message changed everything.",
            "But then I found out something that flipped the whole story.",
            "Wait for the part where they tried to blame me.",
            "The twist at the end made me question my entire perspective.",
        ]
    
    # Vary the prompt structure to encourage different approaches
    structure_variants = [
        "Start with an immediate hook that breaks the pattern. Then add context quickly. Build tension with specific details. Include a twist or unexpected turn. Show the fallout. End with a question that invites debate.",
        "Open with something that makes people stop scrolling. Set the scene in 2-3 sentences. Escalate the conflict with concrete examples. Add a reveal that changes everything. Show how it affected everyone. Close with a question that gets people commenting.",
    ]
    
    structure_guide = random.choice(structure_variants)
    hook_example = random.choice(hook_examples)
    tease_example = random.choice(tease_examples)
    
    prompt = (
        'You are a creative storyteller. Write a 100% ORIGINAL Reddit-style story that feels authentic and engaging.\n\n'
        
        'STORY REQUIREMENTS:\n'
        '- Length: 270-330 words total (hook + tease + story body)\n'
        '- Structure: First line = hook, second line = tease, rest = full story body\n'
        '- Perspective: Write entirely in FIRST PERSON (I, me, my)\n'
        '- Style: Natural, conversational Reddit post style\n'
        '- Include: Specific details, timestamps, names, dialogue, concrete examples\n'
        '- End with: A question that invites comments (e.g., "Am I wrong here?", "What would you do?")\n\n'
        
        f'HOOK EXAMPLE: "{hook_example}"\n'
        f'TEASE EXAMPLE: "{tease_example}"\n\n'
        
        f'{"CREEPY STORY GUIDELINES:" if NICHE == "creepy" else ""}\n'
        f'{"- Build atmosphere with sensory details (sounds, shadows, timing)" if NICHE == "creepy" else ""}\n'
        f'{"- Use specific timestamps and physical details" if NICHE == "creepy" else ""}\n'
        f'{"- Escalate tension gradually from unsettling to terrifying" if NICHE == "creepy" else ""}\n'
        f'{"- Include realistic fear responses" if NICHE == "creepy" else ""}\n\n'
        
        'TITLE:\n'
        '- 50-60 characters, clickable and engaging\n'
        '- Include keywords: "Reddit Story", "AITA", "Storytime", etc.\n'
        '- Examples: "This Reddit Story Will Blow Your Mind", "I Can\'t Believe What My Family Did | AITA"\n\n'
        
        'DESCRIPTION:\n'
        '- 1-2 sentences summarizing the story\n'
        '- Engaging and searchable\n\n'
        
        'OUTPUT JSON FORMAT:\n'
        '{\n'
        '  "title": "Your title here",\n'
        '  "description": "Your description here",\n'
        '  "script": "hook line\\ntease line\\nfull story body ending with question"\n'
        '}\n\n'
        
        f'Theme: {theme}\n'
        f'Niche: {NICHE}\n\n'
        
        'Write the story now. Be creative, authentic, and engaging.'
    )
    return prompt


def call_gemini(prompt):
    """Call Google Gemini API to generate text using the configured model."""
    # Give Gemini enough time for story generation (~60–90s for long outputs)
    request_options = RequestOptions(timeout=90)
    try:
        # Initialize the model with optimized settings for Gemini
        # Try with JSON mode first (for newer models)
        try:
            print(f'  🔄 Trying JSON mode with model: {MODEL_NAME}...')
            model = genai.GenerativeModel(
                model_name=MODEL_NAME,
                generation_config={
                    "temperature": 1.0,  # Good balance of creativity and consistency
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 2048,  # More room for quality output
                    "response_mime_type": "application/json",  # Request JSON format directly
                }
            )
            response = model.generate_content(prompt, request_options=request_options)
            if response.text and response.text.strip():
                print(f'  ✅ JSON mode successful!')
                return response.text
        except Exception as json_error:
            # JSON mode might not be supported, try without it
            error_str = str(json_error)
            if "quota" in error_str.lower() or "429" in error_str:
                raise  # Re-raise quota errors immediately
            print(f'  ⚠️  JSON mode not supported, trying without JSON mode...')
        
        # Fallback: try without JSON mode
        print(f'  🔄 Trying standard mode with model: {MODEL_NAME}...')
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config={
                "temperature": 1.0,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
        )
        response = model.generate_content(prompt, request_options=request_options)
        
        if not response.text or not response.text.strip():
            raise RuntimeError(f"Empty response from Gemini model '{MODEL_NAME}'.")
        
        print(f'  ✅ Standard mode successful!')
        return response.text
    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "429" in error_msg:
            raise RuntimeError(f"Gemini API quota exceeded. Please check your API quota or wait before retrying. Error: {e}")
        elif "404" in error_msg or "not found" in error_msg.lower():
            raise RuntimeError(f"Gemini model '{MODEL_NAME}' not found. Available models: gemini-2.0-flash, gemini-2.5-flash, gemini-2.5-pro")
        else:
            raise RuntimeError(f"Gemini API error: {e}. Make sure GOOGLE_API_KEY is set correctly and the model '{MODEL_NAME}' is available.")


def extract_json(text):
    """Extract JSON from model output. Gemini typically returns clean JSON."""
    if not text or not text.strip():
        raise ValueError('Empty model output')
    
    # Clean up: remove markdown code blocks if present
    import re
    cleaned = text.strip()
    
    # Remove markdown code blocks (```json ... ```)
    cleaned = re.sub(r'```json\s*', '', cleaned, flags=re.I)
    cleaned = re.sub(r'```\s*', '', cleaned)
    
    # Remove control characters except newlines/tabs
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', cleaned)
    
    # Try direct parse first (Gemini should return clean JSON)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # If direct parse fails, try to find JSON block
    start = cleaned.find('{')
    end = cleaned.rfind('}')
    if start == -1 or end == -1:
        raise ValueError('No JSON found in model output')
    
    substring = cleaned[start:end+1]
    
    # Try parsing the substring
    try:
        return json.loads(substring)
    except json.JSONDecodeError as e:
        # Try to fix common JSON issues
        substring = re.sub(r',\s*}', '}', substring)
        substring = re.sub(r',\s*]', ']', substring)
        try:
            return json.loads(substring)
        except Exception as e2:
            raise ValueError(f'Failed to parse JSON: {e2}. Text: {substring[:300]}')


def save_output(obj, theme: str = None):
    """
    Save output with SEO optimization applied to title and description.
    """
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    # Optimize title for SEO
    if 'title' in obj:
        obj['title'] = optimize_title_for_seo(obj['title'], theme or '', NICHE)
    
    # Optimize description for SEO
    if 'description' in obj:
        obj['description'] = optimize_description_for_seo(
            obj['description'], 
            obj.get('title', ''), 
            theme or '', 
            NICHE
        )
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return OUTPUT_PATH


def fallback_story(theme: str):
    """
    Deterministic fallback if Ollama fails to return valid JSON.
    Keeps the same hook + tease + CTA structure so the pipeline always works.
    """
    if NICHE == 'creepy':
        # Creepy-specific fallback templates
        hook_templates = [
            "I woke up at 3:17 AM to the sound of someone trying my door handle.",
            "I thought I was alone in my apartment until I heard footsteps in the hallway.",
            "I found a photo of myself sleeping on my phone that I never took.",
            "Someone has been leaving notes in my apartment, and I live alone.",
            "I keep hearing my name whispered when there's no one else around.",
        ]
        tease_templates = [
            "But what I found next made my blood run cold.",
            "Wait until you hear what the security footage showed.",
            "The twist at the end will make you check your locks.",
            "What happened next is something I still can't explain.",
        ]
        cta_templates = [
            "Has this happened to anyone else?",
            "What would you do in my situation?",
            "Am I overreacting, or should I be worried?",
            "Should I call the police?",
        ]
        hook = random.choice(hook_templates)
        tease = random.choice(tease_templates)
        cta = random.choice(cta_templates)
        
        # Creepy-specific detail bits
        detail_bits = [
            "At 2:43 AM, I heard three distinct knocks on my door, but when I checked, no one was there.",
            "I found footprints outside my window this morning, but it didn't rain last night.",
            "My security camera showed someone entering my apartment at 3:17 AM while I was sleeping.",
            "I received a text from my own number that I didn't send, saying 'I'm watching you.'",
            "I found my front door unlocked this morning, but I know I locked it before bed.",
        ]
        escalation_bits = [
            "Then it happened again the next night at exactly the same time.",
            "Then I found another note, this time with details about my daily routine.",
            "Then my neighbor told me they saw someone looking through my windows last night.",
            "Then I checked my security footage and saw someone had been there multiple times.",
        ]
        detail = random.choice(detail_bits)
        escalation = random.choice(escalation_bits)
        
        body = (
            f"For context, it started with {theme}. "
            f"At first, I thought I was imagining things or being paranoid. "
            f"{detail} "
            f"I tried to rationalize it—maybe it was the wind, or I forgot to lock the door. "
            f"But then {escalation} "
            f"Now I'm not sure if I'm overreacting or if something is seriously wrong. "
            f"I've started checking my locks multiple times before bed, and I can't sleep without my security camera on. "
            f"{cta}"
        )
        
        title_patterns = [
            f"This {theme.title()} Story Will Terrify You | Reddit",
            f"I Can't Explain This {theme.title()} | Scary Story",
            f"Reddit: The {theme.title()} That Haunted Me",
            f"This {theme.title()} Made Me Call The Police",
        ]
        desc_patterns = [
            f"A {theme} story that will make you check your locks. Has this happened to anyone else?",
            f"This {theme} situation has me terrified. What would you do?",
            f"A {theme} story that I still can't explain. Drop your thoughts below!",
        ]
    else:
        hook_templates = [
            "I thought my family was close… until this happened.",
            "I walked into my own home and realized I'd been lied to.",
            "I didn't think a small rule could start a war… I was wrong.",
            "This is the pettiest argument I've ever seen—until the twist.",
        ]
        tease_templates = [
            "Wait for the last message—I still can't believe it.",
            "Wait for what my sibling said at the end.",
            "Wait until you hear the final comment.",
            "Wait for the part that made everyone pick sides.",
        ]
        cta_templates = [
            "Am I overreacting here, or would you be mad too?",
            "Who's wrong—me or them?",
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
            "a receipt with the date/time that didn't line up",
            "a group chat message they 'forgot' to mention",
            "a voicemail that changed the whole story",
            "a calendar invite that proved who agreed to what",
        ]
        escalation_bits = [
            "then they posted a vague story online and people started DM'ing me",
            "then they told our friends I was being 'dramatic' before we even talked",
            "then they changed the agreement like it never existed",
            "then they tried to make it about my tone instead of the actual issue",
        ]
        proof = random.choice(detail_bits)
        escalation = random.choice(escalation_bits)

        body = (
            f"For context, it started with {theme}. "
            f"{a} and I were fine until {b} stepped in and suddenly the story changed depending on who was in the room. "
            "At first I tried to keep it calm and handle it privately, but it kept getting framed like I was the problem. "
            f"Then I found {proof}. "
            f"When I brought it up, {b} acted like I was 'attacking' them and said I was controlling. "
            f"{escalation}. "
            "Now the group chat is split into two teams, and I'm getting blamed for 'starting drama' even though I only responded to what was already being said. "
            f"{cta}"
        )
        
        title_patterns = [
            f"This {theme.title()} Story Will Shock You | Reddit",
            f"I Can't Believe This {theme.title()} | AITA Story",
            f"Reddit: The {theme.title()} That Changed Everything",
            f"This {theme.title()} Drama Split My Family",
        ]
        desc_patterns = [
            f"A {theme} story that will make you question everything. Who's in the wrong here?",
            f"This {theme} situation escalated quickly. What would you do?",
            f"A {theme} story that divided everyone. Drop your thoughts below!",
        ]
    
    script = "\n".join([hook, tease, body])
    title = random.choice(title_patterns)
    description = random.choice(desc_patterns)
    
    return {
        "title": title,
        "description": description,
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
    - Line 1: hook (first person, no labels)
    - Line 2: tease (first person, no labels)
    - Line 3+: body ending with a CTA question (first person throughout)
    This prevents "same script" fallback and makes weak model outputs usable.
    Also enforces first-person perspective and removes all structural labels.
    """
    # Expanded templates for more variety - include creepy-specific if niche is creepy
    if NICHE == 'creepy':
        hook_templates = [
            "I woke up at 3:17 AM to the sound of someone trying my door handle.",
            "I thought I was alone in my apartment until I heard footsteps in the hallway.",
            "I found a photo of myself sleeping on my phone that I never took.",
            "Someone has been leaving notes in my apartment, and I live alone.",
            "I keep hearing my name whispered when there's no one else around.",
            "My security camera caught someone entering my home while I was sleeping.",
            "I found footprints outside my window this morning, but it didn't rain last night.",
            "I received a text from my own number that I didn't send.",
            "I woke up to find my front door unlocked, but I know I locked it.",
            "Every night at 2:43 AM, I hear the same sound outside my window.",
        ]
    else:
        hook_templates = [
            "Stop scrolling—this is actually insane.",
            "I thought this was a small issue… until it blew up.",
            "This comment section would tear you apart.",
            "I didn't expect one rule to start a war.",
            "I'm sitting here at 3 AM wondering if I'm the problem.",
            "My family just had the most ridiculous argument I've ever witnessed.",
            "I thought I knew my friends until last night.",
            "This started as a simple misunderstanding and exploded.",
            "I never thought a group chat could destroy a friendship.",
            "My roommate did something that made me question everything.",
            "I walked into my own home and realized I'd been lied to.",
            "This is the pettiest argument I've ever seen—until the twist.",
            "I thought we were on the same page until I saw the messages.",
            "My best friend just did something that changed everything.",
            "I didn't think boundaries were that hard to understand.",
        ]
    if NICHE == 'creepy':
        tease_templates = [
            "But what I found next made my blood run cold.",
            "Wait until you hear what the security footage showed.",
            "The twist at the end will make you check your locks.",
            "What happened next is something I still can't explain.",
            "But then I discovered something that changed everything.",
            "Wait for the part that made me call the police.",
            "The final detail is what really terrified me.",
            "What I found in my apartment will haunt me forever.",
        ]
    else:
        tease_templates = [
            "Wait for the last comment.",
            "Wait until you hear what they said at the end.",
            "Wait for the twist—seriously.",
            "Wait for the DM I got after this.",
            "But then I found out something that flipped everything.",
            "The last message changed my entire perspective.",
            "Here's what happened next that made it worse.",
            "The twist at the end made me question everything.",
            "But wait until you hear their response.",
            "The part that really got me was what happened after.",
            "I didn't expect what came next.",
            "Then they did something that made it all make sense.",
            "The final message is what really got me.",
            "But the real kicker was what they said at the end.",
            "Wait for the part where they tried to blame me.",
        ]
    if NICHE == 'creepy':
        cta_templates = [
            "Has this happened to anyone else?",
            "What would you do in my situation?",
            "Am I overreacting, or should I be worried?",
            "Should I call the police?",
            "Is this something I should be concerned about?",
            "Has anyone else experienced something like this?",
            "What would you do if this happened to you?",
            "Am I being paranoid, or is this actually dangerous?",
        ]
    else:
        cta_templates = [
            "Who's wrong—me or them?",
            "Team A or Team B?",
            "Am I overreacting, or is this messed up?",
            "What would you do?",
            "Am I the problem here?",
            "Was I out of line, or was this totally unfair?",
            "Who's in the wrong here?",
            "Am I being unreasonable, or are they?",
            "What's your take on this?",
            "Would you have handled this differently?",
            "Am I wrong for feeling this way?",
            "Is this as messed up as I think it is?",
            "What would you do in my situation?",
            "Am I overreacting, or is this actually a big deal?",
            "Who do you think is in the wrong?",
        ]

    raw = (script or "").strip()
    # Strip ALL label formats the model sometimes inserts (HOOK, TEASE, Line 3+, etc.)
    # Remove labels at start of lines
    raw = re.sub(r"^\s*(HOOK\.?|TEASE\.?:?|\[hook\]|\[tease\]|\[story\]|hook:|tease:|Line\s+\d+[:\+]?)\s*", "", raw, flags=re.I | re.M)
    # Remove labels in the middle (like "Line 3+:", "HOOK.", etc.)
    raw = re.sub(r"\b(HOOK\.?|TEASE\.?:?|Line\s+\d+[:\+]?)\s*", "", raw, flags=re.I)
    # Remove formatting markers like ": 'Wait" or colons before quotes (but keep the actual quote)
    raw = re.sub(r":\s*['\"]Wait", "Wait", raw, flags=re.I)
    # Remove standalone colons followed by quotes (like ": 'Why do people...'")
    raw = re.sub(r":\s*['\"]", "", raw)
    # Remove "Line X+:" patterns anywhere
    raw = re.sub(r"Line\s+\d+[:\+]?\s*", "", raw, flags=re.I)
    # Remove any remaining label patterns
    raw = re.sub(r"^\s*HOOK\s*$", "", raw, flags=re.I | re.M)
    raw = re.sub(r"^\s*TEASE\s*$", "", raw, flags=re.I | re.M)
    # Remove standalone colons that are just formatting
    raw = re.sub(r"^\s*:\s*", "", raw, flags=re.M)
    # Remove stray quotes at end of lines (like "Wait for the last comment.'")
    raw = re.sub(r"([^'])'\s*$", r"\1", raw, flags=re.M)
    raw = raw.replace("\r\n", "\n")

    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    # Filter out any lines that are just labels
    lines = [ln for ln in lines if not re.match(r"^(HOOK|TEASE|Line\s+\d+[:\+]?)\s*$", ln, re.I)]
    
    if lines:
        hook = lines[0]
        # Clean hook - remove any label remnants and stray quotes
        hook = re.sub(r"^(HOOK\.?|TEASE\.?:?)\s*", "", hook, flags=re.I).strip()
        hook = re.sub(r"['\"]\s*$", "", hook).strip()  # Remove trailing quotes
        # Remove "Wait for..." from hook if it's there (should be separate)
        hook = re.sub(r"\s*Wait\s+for\s+[^.]*\.?\s*['\"]?\s*$", "", hook, flags=re.I).strip()
        
        # If the model already provided a "wait..." style tease on the next line, keep it.
        if len(lines) > 1 and re.search(r"\bwait\b", lines[1], flags=re.I):
            tease = lines[1]
            # Clean tease
            tease = re.sub(r"^(HOOK\.?|TEASE\.?:?)\s*", "", tease, flags=re.I).strip()
            tease = re.sub(r"['\"]\s*$", "", tease).strip()  # Remove trailing quotes
            body = " ".join(lines[2:]) if len(lines) > 2 else ""
        else:
            tease = random.choice(tease_templates)
            body = " ".join(lines[1:])
        
        # Remove duplicate teases from body
        body = re.sub(r"\bWait\s+for\s+[^.]*\.?\s*['\"]?\s*", "", body, flags=re.I)
    else:
        sentences = _split_sentences(raw)
        if sentences:
            hook = sentences[0]
            # Clean hook - remove labels
            hook = re.sub(r"\b(HOOK\.?|TEASE\.?:?|Line\s+\d+[:\+]?)\s*", "", hook, flags=re.I).strip()
            # Ensure first person
            if not re.search(r"\b(I|me|my|myself)\b", hook, re.I):
                hook = re.sub(r"^(He|She|They|It|The)\s+", "I ", hook, flags=re.I)
            body = " ".join(sentences[1:]) if len(sentences) > 1 else ""
        else:
            hook = random.choice(hook_templates)
            body = ""
        tease = random.choice(tease_templates)

    # Preserve more of the original script - only fix if absolutely necessary
    body_word_count = _word_count(body)
    
    # Light touch: only fix obvious third-person narration (not dialogue)
    # Allow third person in quoted dialogue ("He said...") but fix narrative third person
    # Check for sentences that start with third-person subjects in narrative (not in quotes)
    body_lines = body.split('. ')
    fixed_lines = []
    for line in body_lines:
        # Only fix if it's clearly narrative third person (not dialogue)
        # Skip if line contains quotes (likely dialogue)
        if '"' not in line and "'" not in line:
            # If line starts with third person subject, try to convert to first person context
            if re.match(r"^(He|She|They)\s+(was|were|said|did|went|got|felt|thought|is|are|started|decided|tried)\b", line, re.I):
                # Convert to first person perspective
                line = re.sub(r"^(He|She|They)\s+(was|were|said|did|went|got|felt|thought|is|are|started|decided|tried)\b", "I was", line, flags=re.I)
        fixed_lines.append(line)
    body = '. '.join(fixed_lines)
    
    # Light cleanup: only fix obvious narrator perspective issues
    body = re.sub(r"\b(their younger sibling|their sibling)\b", "my sibling", body, flags=re.I)
    body = re.sub(r"\b(their parents|their family)\b", "my family", body, flags=re.I)
    
    # Only pad if body is significantly short - preserve original content
    if body_word_count < 200:
        # Add minimal context to reach target length (all in first person)
        if NICHE == 'creepy':
            pad = (
                f"For context, it started with {theme}. "
                "At first, I thought I was imagining things or being paranoid. "
                "I tried to rationalize it—maybe it was the wind, or I was just tired. "
                "But then it happened again, and I started to realize something was really wrong. "
                "Now I'm not sure if I'm overreacting or if I should be genuinely concerned."
            )
        else:
            pad = (
                f"For context, it started with {theme}. "
                "At first it seemed manageable, but things escalated quickly. "
                "I tried to handle it calmly, but the situation kept getting more complicated. "
                "Now I'm not sure if I'm overreacting or if this is actually a bigger deal than I thought."
            )
        body = (body + " " + pad).strip()

    # Ensure ending CTA question
    if not body.endswith("?"):
        body = body.rstrip()
        # If it already ends in punctuation, just add CTA. Otherwise add a question mark CTA.
        body = body + " " + random.choice(cta_templates)
        if not body.endswith("?"):
            body = body.rstrip(".! ") + "?"
    
    # Final cleanup: remove any remaining label patterns from all parts
    hook = re.sub(r"\b(HOOK\.?|TEASE\.?:?|Line\s+\d+[:\+]?)\s*", "", hook, flags=re.I).strip()
    tease = re.sub(r"\b(HOOK\.?|TEASE\.?:?|Line\s+\d+[:\+]?)\s*", "", tease, flags=re.I).strip()
    body = re.sub(r"\b(HOOK\.?|TEASE\.?:?|Line\s+\d+[:\+]?)\s*", "", body, flags=re.I).strip()
    
    # Ensure first person in hook and tease too
    if hook and not re.search(r"\b(I|me|my|myself)\b", hook, re.I):
        # If hook doesn't have first person, try to fix it
        hook = re.sub(r"^(He|She|They|It)\s+", "I ", hook, flags=re.I)
    
    if tease and not re.search(r"\b(I|me|my|myself|wait)\b", tease, re.I):
        # Tease can be about waiting, but if it has third person, fix it
        tease = re.sub(r"\b(He|She|They)\s+", "I ", tease, flags=re.I)

    return "\n".join([hook, tease, body]).strip()


def main():
    # Randomize theme selection for more variety
    theme = random.choice(theme_list)
    print('\n' + '=' * 70)
    print('🎬 YOUTUBE SHORTS SCRIPT GENERATOR')
    print('=' * 70)
    print(f'Theme: {theme}')
    print(f'Using Gemini model: {MODEL_NAME}')
    print('=' * 70 + '\n')
    
    prompt = build_prompt(theme)
    gemini_success = False

    # One retry: if parsing fails, try again with a stricter instruction
    for attempt in range(2):
        if attempt == 1:
            print('🔄 Retrying with stricter JSON-only instruction...')
            prompt = 'IMPORTANT: Return ONLY valid JSON, no markdown, no backticks, no explanations. JSON schema: {"title": "...", "description": "...", "script": "..."}\n\n' + prompt
            time.sleep(1)
        
        print(f'📡 Attempting Gemini API call (attempt {attempt + 1}/2)...')
        try:
            raw = call_gemini(prompt)
            print('✅ Gemini API call successful!')
            gemini_success = True
        except Exception as e:
            error_msg = str(e)
            if "quota" in error_msg.lower() or "429" in error_msg:
                print(f'❌ Gemini API quota exceeded: {e}')
                print('⚠️  Will use fallback template script')
            elif "404" in error_msg or "not found" in error_msg.lower():
                print(f'❌ Gemini model not found: {e}')
                print('⚠️  Will use fallback template script')
            else:
                print(f'❌ Gemini API call failed (attempt {attempt + 1}/2): {e}')
            
            if attempt == 1:
                # Last attempt failed, use fallback
                print('\n⚠️  All Gemini API attempts failed. Using fallback template script...')
                break
            continue

        if not gemini_success:
            continue

        try:
            print('🔍 Parsing JSON response from Gemini...')
            obj = extract_json(raw)
            print('✅ JSON parsed successfully')
        except Exception as e:
            print(f'❌ Failed to parse JSON from model output: {e}')
            print('📄 Model output preview:\n', raw[:500] + '...' if len(raw) > 500 else raw)
            continue

        # Validate
        print('🔍 Validating output structure...')
        validation_failed = False
        for k in ('title', 'description', 'script'):
            if k not in obj:
                print(f"❌ Output missing '{k}'")
                print('📄 Model output was:\n', raw[:500])
                validation_failed = True
                break

            # Some models mistakenly return script as an object; reject so we retry.
            if k == 'script' and not isinstance(obj[k], str):
                print(f"❌ Output has invalid 'script' (must be a string, not an object).")
                print('📄 Model output was:\n', raw[:500])
                validation_failed = True
                break

            if not isinstance(obj[k], str) or not obj[k].strip():
                print(f"❌ Output missing or invalid '{k}'")
                if attempt == 1:
                    print('📄 Model output was:\n', raw[:500])  # Show first 500 chars
                validation_failed = True
                break
        
        if validation_failed:
            continue
        
        print('✅ Output validation passed')
        
        # Light normalization - Gemini should already follow the format well
        # Only normalize if script doesn't have proper structure
        script_lines = obj["script"].split('\n')
        if len(script_lines) < 2 or not any('?' in line for line in script_lines[-3:]):
            print('🔧 Normalizing script structure...')
            obj["script"] = normalize_script(obj["script"], theme)
        
        # Validate script length (should be 270-330 words, accept 240-360)
        word_count = _word_count(obj["script"])
        if word_count < 240:
            print(f"⚠️  Warning: Script is short ({word_count} words, target 270-330), but continuing...")
        elif word_count > 360:
            print(f"⚠️  Warning: Script is long ({word_count} words, target 270-330), but continuing...")
        elif 270 <= word_count <= 330:
            print(f"✅ Script length: {word_count} words (target: 270-330)")

        # Apply SEO optimization before saving
        print('📝 Applying SEO optimization...')
        out_path = save_output(obj, theme)
        print('\n' + '=' * 70)
        print('✅ SUCCESS - Generated script using Gemini API')
        print('=' * 70)
        print(f'📁 Saved to: {out_path}')
        print(f'📊 SEO Title: {obj["title"]} ({len(obj["title"])} chars)')
        print(f'📏 Word count: {word_count} words')
        print('\n📄 Preview:\n')
        print('Title:', obj['title'])
        print('\nDescription:\n', obj['description'])
        print('\nScript (first 200 chars):\n', obj['script'][:200] + '...' if len(obj['script']) > 200 else obj['script'])
        print('\n' + '=' * 70)
        return

    # If we get here, all attempts failed - use fallback
    print('\n' + '=' * 70)
    print('⚠️  FALLBACK MODE - Using template script')
    print('=' * 70)
    print('Reason: Gemini API unavailable or failed')
    print('=' * 70 + '\n')
    
    obj = fallback_story(theme)
    out_path = save_output(obj, theme)
    
    print('✅ Saved fallback script to', out_path)
    print(f'📊 SEO Title: {obj["title"]} ({len(obj["title"])} chars)')
    word_count = _word_count(obj["script"])
    print(f'📏 Word count: {word_count} words')
    print('\n📄 Preview:\n')
    print('Title:', obj['title'])
    print('\nDescription:\n', obj['description'])
    print('\nScript (first 200 chars):\n', obj['script'][:200] + '...' if len(obj['script']) > 200 else obj['script'])
    print('\n' + '=' * 70)


if __name__ == '__main__':
    main()
