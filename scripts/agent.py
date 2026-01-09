#!/usr/bin/env python3
"""
Agent to fetch a Reddit post, rewrite it with OpenAI, and save as JSON for YouTube Shorts.
Phase 1 only: script generation.
"""

import os
import random
import json
from dotenv import load_dotenv
import openai
import praw

# Load environment
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "yt-shorts-agent")

if not OPENAI_API_KEY or not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
    raise SystemExit("Missing required environment variables. Copy .env.example to .env and set your keys.")

openai.api_key = OPENAI_API_KEY

# Initialize Reddit client
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT,
)

SUBREDDITS = ["TrueOffMyChest", "AmItheAsshole", "relationship_advice"]
MAX_CHARS = 2500
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "script.json")


def pick_post(retries=10):
    """Pick a random suitable post from the configured subreddits."""
    subs = SUBREDDITS.copy()
    random.shuffle(subs)
    for _ in range(retries):
        subreddit_name = random.choice(subs)
        subreddit = reddit.subreddit(subreddit_name)
        # Fetch hot posts and filter
        for submission in subreddit.hot(limit=50):
            if submission.stickied:
                continue
            if submission.over_18:
                continue
            # Prefer text posts with body
            text = (submission.selftext or "").strip()
            title = (submission.title or "").strip()
            full_text = f"{title}\n\n{text}" if text else title
            if not full_text:
                continue
            if len(full_text) > MAX_CHARS:
                # truncate gracefully
                full_text = full_text[:MAX_CHARS]
            # Heuristic: require at least ~200 chars to be story-like
            if len(full_text) < 200:
                continue
            return submission, full_text
    return None, None


def build_prompt(post_text):
    """Construct the prompt to send to OpenAI following the rules."""
    system = (
        "You are a creative assistant that rewrites Reddit posts into short, engaging scripts for YouTube Shorts. "
        "Follow the user instructions exactly and output ONLY valid JSON with the schema: {\n  \"title\": \"\",\n  \"description\": \"\",\n  \"script\": \"\"\n}\n"
    )

    user = (
        "Rewrite the following Reddit post into original wording. Do NOT quote the original text. "
        "Remove usernames and any identifying details. Produce a 30–40 second spoken script (about 90–130 words). "
        "Start with a hook and end with a question. Avoid explicit sexual content or graphic violence. "
        "Append the tag '#shorts' to the description. Return ONLY valid JSON with keys: title, description, script. "
        f"Here is the post:\n\n{post_text}"
    )

    return system, user


def call_openai(system_prompt, user_prompt):
    """Call the OpenAI ChatCompletion API using gpt-4o-mini."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
            max_tokens=500,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise


def save_output(json_text):
    """Save JSON text to output/script.json"""
    # Ensure output directory exists
    out_dir = os.path.dirname(OUTPUT_PATH)
    os.makedirs(out_dir, exist_ok=True)
    # Parse and reformat JSON to ensure validity
    data = json.loads(json_text)
    # Ensure description has #shorts
    if "description" in data:
        if "#shorts" not in data["description"]:
            data["description"] = data["description"].strip() + "\n\n#shorts"
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return OUTPUT_PATH


def main():
    submission, post_text = pick_post()
    if not submission:
        print("No suitable post found. Try again later.")
        return

    print(f"Selected post: {submission.title} (r/{submission.subreddit.display_name})")

    system_prompt, user_prompt = build_prompt(post_text)

    print("Calling OpenAI to rewrite the post...")
    ai_output = call_openai(system_prompt, user_prompt)

    # Attempt to extract JSON from the model output
    # Some models may wrap JSON in backticks or markdown; try to find the first '{' and last '}'
    start = ai_output.find("{")
    end = ai_output.rfind("}")
    if start == -1 or end == -1:
        print("OpenAI returned invalid JSON.")
        print(ai_output)
        return
    json_text = ai_output[start : end + 1]

    try:
        out_path = save_output(json_text)
    except Exception as e:
        print("Failed to save output:", e)
        print("Model output was:\n", ai_output)
        return

    print(f"Saved generated script to {out_path}")
    print("Preview:")
    with open(out_path, "r", encoding="utf-8") as f:
        print(f.read())


if __name__ == "__main__":
    main()
