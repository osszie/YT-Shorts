#!/usr/bin/env python3
"""
Generate ASS subtitle file with word-level bouncing captions.
Each word pops/bounces as it's spoken, similar to TikTok style.
"""
import json
import os
import re
import subprocess
import sys
import ssl
import argparse
import math

# Fix SSL certificate issues for Whisper model download
ssl._create_default_https_context = ssl._create_unverified_context

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

ROOT = os.path.dirname(os.path.dirname(__file__))
SCRIPT_JSON = os.path.join(ROOT, "output", "script.json")
VOICE_MP3 = os.path.join(ROOT, "output", "voice.mp3")
OUT_ASS = os.path.join(ROOT, "output", "captions.ass")

# Layout constants
CHARS_PER_LINE = 25  # Target characters per line (22-28 range)
MAX_LINES = 2  # Maximum lines displayed at once
CENTER_Y_START = 900  # Starting Y position for center (1080x1920 video, center is ~960)
LINE_HEIGHT = 80  # Vertical spacing between lines
CENTER_X = 540  # Center X position (1080 width)

# Timing constants
MIN_WORD_DURATION = 0.18  # Minimum duration per word (seconds) - matches natural speech pace
MAX_WORD_DURATION = 0.55  # Maximum duration per word (seconds) - for longer words
TIMING_DELAY = 0.25  # Delay at start to sync with audio (allows TTS to start)
WORD_PAUSE = 0.03  # Small pause between words (reduced for tighter sync)

# Caption offset (seconds). Positive delays captions; negative makes them earlier.
# Useful to fix small intro sync issues caused by audio encoder/decoder priming.
DEFAULT_CAPTION_OFFSET = 0.0

# ASS timestamps are centisecond precision; very short words can collapse to 0-length after rounding.
# We enforce a minimum on-screen duration to avoid "missing words".
MIN_WORD_ONSCREEN_SECONDS = 0.12

# Hook/Highlight tuning
HOOK_WINDOW_SECONDS = 2.0  # first ~2s: bigger + brighter
HIGHLIGHT_COLOR = "&H00A5FF&"  # orange-ish (BGR)

# Common Reddit-story "spike" words to emphasize
KEYWORDS = {
    "aita", "update", "wedding", "dress", "code", "debate", "fiancé", "fiance", "mil", "sil",
    "roommate", "boss", "cheated", "divorce", "banned", "kicked", "stole", "lied",
    "comment", "comments", "question", "truth", "caught", "exposed", "plot", "twist",
    "formal", "casual", "rules", "etiquette",
}


def _clean_word(w: str) -> str:
    return re.sub(r"[^\w']+", "", (w or "")).strip().lower()


def build_word_style_tags(word: str, start_s: float, idx: int) -> str:
    """
    Extra per-word styling:
    - Hook window: bigger scale + stronger glow + slightly thicker outline
    - Keyword highlight: change color for emphasis
    """
    tags = []

    clean = _clean_word(word)
    is_keyword = (clean in KEYWORDS) or (clean.isupper() and len(clean) >= 3)

    # Hook punch: bigger + brighter in first ~2 seconds
    if start_s <= HOOK_WINDOW_SECONDS:
        # Scale up and increase glow/outline a bit for the hook
        tags.append("\\bord10\\shad6\\be6\\fscx130\\fscy130")

    # Keyword highlight
    if is_keyword:
        tags.append(f"\\1c{HIGHLIGHT_COLOR}")

    return "{" + "".join(tags) + "}" if tags else ""


def _floor_cs(t: float) -> float:
    return math.floor(t * 100.0) / 100.0


def _ceil_cs(t: float) -> float:
    return math.ceil(t * 100.0) / 100.0


def sanitize_word_timings(word_timings, total_duration):
    """
    Make timings safe for ASS rendering:
    - Monotonic, non-overlapping
    - Minimum visible duration
    - Start floored to centiseconds, end ceiled to centiseconds (prevents Start==End)
    """
    if not word_timings:
        return []

    out = []
    prev_end = 0.0
    for word, start, end in word_timings:
        s = 0.0 if start is None else float(start)
        e = s if end is None else float(end)

        # Clamp into [0, total_duration]
        s = max(0.0, min(s, total_duration))
        e = max(0.0, min(e, total_duration))

        # Ensure non-decreasing
        if s < prev_end:
            s = prev_end
        if e < s:
            e = s

        # Enforce minimum duration (in real seconds)
        if (e - s) < MIN_WORD_ONSCREEN_SECONDS:
            e = min(total_duration, s + MIN_WORD_ONSCREEN_SECONDS)

        # Quantize to ASS centiseconds in a safe way
        s_q = _floor_cs(s)
        e_q = _ceil_cs(e)
        if e_q <= s_q:
            e_q = min(total_duration, s_q + 0.01)

        out.append((word, s_q, e_q))
        prev_end = e_q

    # Ensure last word ends exactly at duration (quantized)
    if out:
        w, s, _ = out[-1]
        out[-1] = (w, s, _ceil_cs(total_duration))

    return out


def apply_global_offset(word_timings, offset_seconds, clamp_end=None):
    """Shift all word timings by a constant offset; clamp to >=0 (and optionally <= clamp_end)."""
    if not word_timings or abs(offset_seconds) < 1e-9:
        return word_timings
    out = []
    for word, start, end in word_timings:
        s = (start or 0.0) + offset_seconds
        e = (end or 0.0) + offset_seconds
        s = max(0.0, s)
        e = max(0.0, e)
        if clamp_end is not None:
            s = min(s, clamp_end)
            e = min(e, clamp_end)
        # Ensure non-zero duration so ASS renderer shows it
        if e <= s:
            e = min((s + 0.05), clamp_end) if clamp_end is not None else (s + 0.05)
        out.append((word, s, e))
    return out


def check_ffprobe():
    """Check if ffprobe is available."""
    try:
        subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ ffprobe not found. Install FFmpeg:")
        print("   brew install ffmpeg")
        sys.exit(1)


def get_audio_duration(mp3_path):
    """Get audio duration in seconds using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            mp3_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"❌ Failed to get audio duration: {e}")
        sys.exit(1)


def split_into_words(text):
    """
    Split text into words, keeping punctuation attached.
    Returns list of (word, char_count) tuples.
    """
    # Split by whitespace but keep punctuation with words
    words = re.findall(r'\S+', text)
    return [(word, len(word)) for word in words]


def get_word_timestamps_from_audio(audio_path, script_text=None):
    """
    Use Whisper to get exact word-level timestamps from audio (CapCut-style auto captions).
    Returns list of (word, start_time, end_time) tuples directly from Whisper.
    No matching to script - uses what Whisper actually hears for perfect sync.
    """
    if not WHISPER_AVAILABLE:
        print("⚠️  Whisper not available, falling back to estimated timings")
        return None
    
    print("🎤 Using Whisper for auto captions (CapCut-style)...")
    print("   Transcribing audio directly - using exact word timestamps from speech recognition")
    
    try:
        # Load Whisper model
        model = whisper.load_model("medium")
        
        # Transcribe with word-level timestamps
        # IMPORTANT: Do NOT pass `initial_prompt` here.
        # When the prompt contains the beginning of the script, Whisper can treat it as
        # "already said" context and start emitting words later (causing missing intro words).
        result = model.transcribe(
            audio_path,
            word_timestamps=True,
            language="en",
            initial_prompt=None,
            fp16=False,  # default to fp32 on CPU to avoid FP16 warning spam
        )
        
        # Extract word timestamps directly from Whisper (CapCut-style)
        word_timings = []
        for segment in result.get("segments", []):
            for word_info in segment.get("words", []):
                word = word_info.get("word", "").strip()
                start = word_info.get("start", 0)
                end = word_info.get("end", 0)
                if word:  # Include all words
                    word_timings.append((word, start, end))
        
        if word_timings:
            print(f"✅ Extracted {len(word_timings)} words with exact timestamps from audio")
            return word_timings
        else:
            print("⚠️  No word timestamps found, falling back to estimated timings")
            return None
            
    except Exception as e:
        print(f"⚠️  Whisper error: {e}")
        print("   Falling back to estimated timings")
        return None


def match_words_to_timestamps(words, whisper_timings):
    """
    Match our word list to Whisper timestamps using sequence alignment.
    Handles differences in word splitting/punctuation.
    """
    if not whisper_timings:
        return None
    
    def normalize_word(w):
        """Normalize word for matching - remove punctuation, lowercase, handle contractions."""
        # Remove all punctuation
        cleaned = re.sub(r'[^\w\s]', '', w).lower().strip()
        # Handle common contractions
        cleaned = cleaned.replace("'", "").replace("'", "")
        return cleaned
    
    # Build normalized word lists for matching
    our_words_normalized = [normalize_word(word) for word, _ in words]
    whisper_words_normalized = [normalize_word(w) for w, _, _ in whisper_timings]
    
    # Simple greedy matching with lookahead
    matched = []
    whisper_idx = 0
    
    for word_idx, (word, _) in enumerate(words):
        clean_word = our_words_normalized[word_idx]
        
        # Try to find matching word in Whisper results
        best_match = None
        best_idx = whisper_idx
        
        # Look ahead up to 15 words for a match (more flexible)
        for i in range(whisper_idx, min(whisper_idx + 15, len(whisper_timings))):
            whisper_word, start, end = whisper_timings[i]
            clean_whisper = whisper_words_normalized[i]
            
            # Exact match
            if clean_word == clean_whisper:
                best_match = (word, start, end)
                best_idx = i + 1
                break
            # Partial match (word contains whisper word or vice versa)
            elif clean_word and clean_whisper:
                # Check if they're similar (one contains the other, or they're very close)
                if clean_word in clean_whisper or clean_whisper in clean_word:
                    if best_match is None:
                        best_match = (word, start, end)
                        best_idx = i + 1
                # Check if they're similar length and share most characters
                elif abs(len(clean_word) - len(clean_whisper)) <= 2:
                    # Simple similarity check
                    common_chars = sum(1 for c in clean_word if c in clean_whisper)
                    if common_chars >= min(len(clean_word), len(clean_whisper)) * 0.7:
                        if best_match is None:
                            best_match = (word, start, end)
                            best_idx = i + 1
        
        if best_match:
            matched.append(best_match)
            whisper_idx = best_idx
        else:
            # No match found, use estimated timing (will be filled in later)
            matched.append((word, None, None))
            # Don't advance whisper_idx too much, might match next word
            # But advance slightly to avoid getting stuck
            if whisper_idx < len(whisper_timings) - 1:
                whisper_idx = min(whisper_idx + 1, len(whisper_timings) - 1)
    
    return matched if matched else None


def calculate_word_timings(words, total_duration):
    """
    Calculate timing for each word to better match natural speech.
    Uses word count for more even distribution, with character-based adjustments.
    Returns list of (word, start_time, end_time) tuples.
    """
    if not words:
        return []
    
    # Reserve time for delay and pauses between words
    num_words = len(words)
    total_pause_time = (num_words - 1) * WORD_PAUSE  # Pauses between words
    available_duration = total_duration - TIMING_DELAY - total_pause_time
    
    if available_duration <= 0:
        available_duration = total_duration - TIMING_DELAY
        total_pause_time = 0
    
    # Base duration per word (more even distribution)
    base_duration_per_word = available_duration / num_words if num_words > 0 else 0
    
    # Calculate total "weight" for proportional adjustment
    # Longer words get slightly more time, but not as much as before
    total_weight = 0
    word_weights = []
    for word, char_count in words:
        # Weight based on word length, but less extreme
        # Short words (1-3 chars): 0.8x, Medium (4-6): 1.0x, Long (7+): 1.2x
        if char_count <= 3:
            weight = 0.8
        elif char_count <= 6:
            weight = 1.0
        else:
            weight = 1.2
        word_weights.append(weight)
        total_weight += weight
    
    timings = []
    current_time = TIMING_DELAY  # Start after delay to sync with audio
    
    for i, (word, char_count) in enumerate(words):
        # Calculate duration: base + proportional adjustment
        weight = word_weights[i]
        proportion = weight / total_weight if total_weight > 0 else 1.0 / num_words
        duration = available_duration * proportion
        
        # Enforce min/max duration
        duration = max(MIN_WORD_DURATION, min(MAX_WORD_DURATION, duration))
        
        # Don't exceed remaining time
        remaining = total_duration - current_time
        if remaining <= 0:
            break
        
        duration = min(duration, remaining)
        
        start_time = current_time
        end_time = current_time + duration
        
        timings.append((word, start_time, end_time))
        
        # Move to next word with a small pause (except for last word)
        if i < len(words) - 1:
            current_time = end_time + WORD_PAUSE
        else:
            current_time = end_time
    
    # Ensure last word ends exactly at total_duration
    if timings:
        timings[-1] = (timings[-1][0], timings[-1][1], total_duration)
    
    return timings


def layout_words(words_with_timings):
    """
    Layout words into lines (max 2 lines visible at once).
    Returns list of (word, start, end, line_num, x_pos, y_pos) tuples.
    """
    # Group words into lines based on character count
    all_lines = []
    current_line = []
    current_line_chars = 0
    
    for word, start, end in words_with_timings:
        word_chars = len(word)
        space_needed = 1 if current_line_chars > 0 else 0
        
        # Check if adding this word would exceed line length
        if current_line and (current_line_chars + space_needed + word_chars) > CHARS_PER_LINE:
            # Start new line
            all_lines.append(current_line)
            current_line = [(word, start, end)]
            current_line_chars = word_chars
        else:
            # Add to current line
            current_line.append((word, start, end))
            current_line_chars += word_chars + space_needed
    
    # Add remaining line
    if current_line:
        all_lines.append(current_line)
    
    # Now assign positions to all words, showing max 2 lines at once
    result = []
    
    for word_idx, (word, start, end) in enumerate(words_with_timings):
        # Find which line this word belongs to
        line_idx = 0
        char_count = 0
        for line in all_lines:
            for w, _, _ in line:
                if w == word and char_count <= word_idx:
                    break
                char_count += 1
            if char_count > word_idx:
                break
            line_idx += 1
        
            # Calculate which of the last 2 lines this is (for positioning)
            # We want to show the 2 most recent lines
            total_lines = len(all_lines)
            if total_lines <= MAX_LINES:
                display_line_idx = line_idx
            else:
                # Show last 2 lines, so map line_idx to 0 or 1
                if line_idx >= total_lines - MAX_LINES:
                    display_line_idx = line_idx - (total_lines - MAX_LINES)
                else:
                    # Word is too old, don't display (but we'll display it anyway for now)
                    display_line_idx = 0
            
            y_pos = CENTER_Y_START + (display_line_idx * LINE_HEIGHT)
        
        # Find the line this word is in
        word_line = None
        for line in all_lines:
            if any(w == word for w, _, _ in line):
                word_line = line
                break
        
        if word_line:
            # Calculate X position within the line
            line_text = " ".join(w for w, _, _ in word_line)
            # Approximate: each character is ~35 pixels wide at 48px font
            line_width = len(line_text) * 35
            start_x = CENTER_X - (line_width // 2)
            
            # Find position of this word in the line
            current_x = start_x
            word_found = False
            for w, _, _ in word_line:
                word_width = len(w) * 35
                if w == word:
                    word_x = current_x + (word_width // 2)
                    result.append((word, start, end, display_line_idx, word_x, y_pos))
                    word_found = True
                    break
                current_x += word_width + 35  # 35px for space
            
            if not word_found:
                # Fallback: center the word
                result.append((word, start, end, display_line_idx, CENTER_X, y_pos))
        else:
            # Fallback: center the word
            result.append((word, start, end, display_line_idx, CENTER_X, y_pos))
    
    return result


def format_ass_time(seconds):
    """Convert seconds to ASS time format: H:MM:SS.cc"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def create_bounce_animation():
    """
    Create bounce animation tags for a word with glow effect.
    Bounce: start smaller (80%), pop bigger (115%), settle to normal (100%).
    Glow: blur edges effect when word is active.
    Duration: 0ms -> 120ms -> 220ms
    """
    # \fscx and \fscy control font scale (percentage)
    # \be controls blur edges (glow effect) - higher value = more glow
    # \t(start, end, tags) applies tags over time range
    return (
        "{\\fscx80\\fscy80\\be2"  # Start at 80% size, minimal glow
        "\\t(0,120,\\fscx115\\fscy115\\be5)"  # Pop to 115% with strong glow (120ms)
        "\\t(120,220,\\fscx100\\fscy100\\be3)}"  # Settle to 100% with medium glow (220ms)
    )


def write_ass_file(word_layouts, output_path):
    """Write ASS file with word-level bouncing captions."""
    with open(output_path, "w", encoding="utf-8") as f:
        # ASS header - MUST include PlayResX/Y for proper positioning
        f.write("[Script Info]\n")
        f.write("Title: Word-Level Bouncing Captions\n")
        f.write("ScriptType: v4.00+\n")
        f.write("PlayResX: 1080\n")
        f.write("PlayResY: 1920\n\n")
        
        # Styles
        f.write("[V4+ Styles]\n")
        f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
        # Bright yellow text, thick black outline, bold, large font, center-bottom alignment
        # PrimaryColour: &H00ffff = bright yellow (BGR: B=00, G=ff, R=ff)
        # OutlineColour: &H000000 = black
        # BackColour: &H00000000 = transparent (no background box)
        # BorderStyle: 0 = no background box (was 4 = opaque box)
        # Outline: 8px (very thick for visibility)
        # Shadow: 4px
        # Alignment: 5 = center-bottom
        f.write("Style: Default,Arial,72,&H00ffff,&H00ffff,&H000000,&H00000000,1,0,0,0,100,100,0,0,0,8,4,5,10,10,10,1\n\n")
        
        # Events
        f.write("[Events]\n")
        f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        
        # Write each word as a separate Dialogue line
        for idx, (word, start, end, line_idx, x_pos, y_pos) in enumerate(word_layouts):
            bounce_tags = create_bounce_animation()
            pos_tag = f"{{\\pos({x_pos},{y_pos})}}"
            extra_style = build_word_style_tags(word, float(start), idx)
            
            # Combine all tags: position + bounce animation
            all_tags = f"{pos_tag}{extra_style}{bounce_tags}"
            
            # Write dialogue line
            f.write(f"Dialogue: 0,{format_ass_time(start)},{format_ass_time(end)},Default,,0,0,0,,{all_tags}{word}\n")


def main():
    check_ffprobe()

    parser = argparse.ArgumentParser(description="Generate ASS bouncing captions.")
    parser.add_argument(
        "--offset",
        type=float,
        default=DEFAULT_CAPTION_OFFSET,
        help="Global caption time offset in seconds. Positive delays captions; negative makes them earlier.",
    )
    args = parser.parse_args()
    
    if not os.path.exists(SCRIPT_JSON):
        print("❌ Missing output/script.json. Run: python scripts/agent.py first.")
        sys.exit(1)
    
    if not os.path.exists(VOICE_MP3):
        print("❌ Missing output/voice.mp3. Run: python scripts/tts.py first.")
        sys.exit(1)
    
    # Load script
    with open(SCRIPT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    script_text = (data.get("script") or "").strip()
    if not script_text:
        print("❌ output/script.json is missing the 'script' field.")
        sys.exit(1)
    
    # Get audio duration
    duration = get_audio_duration(VOICE_MP3)
    print(f"Audio duration: {duration:.2f} seconds")
    
    # Get word-level timestamps directly from Whisper (CapCut-style auto captions)
    whisper_timings = get_word_timestamps_from_audio(VOICE_MP3, script_text)
    
    if whisper_timings:
        # Use Whisper's direct timestamps - no matching, no interpolation
        # This gives perfect sync like CapCut auto captions
        word_timings = whisper_timings
        print(f"✅ Using {len(word_timings)} words with exact timestamps from Whisper")
        print(f"   Perfect sync - using what Whisper actually heard in the audio")
    else:
        # Fallback: split script and estimate timings
        words = split_into_words(script_text)
        print(f"Split into {len(words)} words")
        word_timings = calculate_word_timings(words, duration)
        print(f"⚠️  Calculated estimated timings for {len(word_timings)} words")

    # Always sanitize timings so ASS can't drop words due to rounding/zero-length events.
    word_timings = sanitize_word_timings(word_timings, duration)

    if args.offset:
        word_timings = apply_global_offset(word_timings, args.offset, clamp_end=duration)
        print(f"⏱️  Applied global caption offset: {args.offset:+.3f}s")
    
    # Layout words
    word_layouts = layout_words(word_timings)
    print(f"Laid out {len(word_layouts)} words into lines")
    
    # Write ASS file
    os.makedirs(os.path.dirname(OUT_ASS), exist_ok=True)
    write_ass_file(word_layouts, OUT_ASS)
    
    print(f"✅ Saved bouncing captions to: {OUT_ASS}")
    print(f"   {len(word_layouts)} word-level captions with bounce animation")


if __name__ == "__main__":
    main()
