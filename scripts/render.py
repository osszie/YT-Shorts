#!/usr/bin/env python3
"""
Render final video with background, voice, and burned-in captions.
Uses FFmpeg to create 1080x1920 vertical video.
"""
import os
import random
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
BACKGROUNDS_DIR = os.path.join(ROOT, "assets", "backgrounds")
VOICE_MP3 = os.path.join(ROOT, "output", "voice.mp3")
CAPTIONS_SRT = os.path.join(ROOT, "output", "captions.srt")
CAPTIONS_ASS = os.path.join(ROOT, "output", "captions.ass")
OUT_MP4 = os.path.join(ROOT, "output", "final.mp4")


def check_ffmpeg():
    """Check if ffmpeg and ffprobe are available."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ FFmpeg not found. Install it:")
        print("   brew install ffmpeg")
        sys.exit(1)


def get_video_duration(video_path):
    """Get video duration in seconds using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"❌ Failed to get video duration: {e}")
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


def pick_background():
    """Pick a random background video from assets/backgrounds/."""
    if not os.path.exists(BACKGROUNDS_DIR):
        print(f"❌ Backgrounds directory not found: {BACKGROUNDS_DIR}")
        print("   Create the directory and add .mp4 background videos.")
        sys.exit(1)
    
    try:
        backgrounds = [f for f in os.listdir(BACKGROUNDS_DIR) if f.endswith('.mp4')]
    except OSError as e:
        print(f"❌ Error reading backgrounds directory: {e}")
        sys.exit(1)
    
    if not backgrounds:
        print(f"❌ No .mp4 files found in {BACKGROUNDS_DIR}")
        print("   Add background video files (.mp4) to this directory.")
        sys.exit(1)
    
    background_file = random.choice(backgrounds)
    background_path = os.path.join(BACKGROUNDS_DIR, background_file)
    print(f"Using background: {background_file}")
    return background_path


def get_random_start_time(background_path, audio_duration):
    """
    Get a random start time in the background video.
    Ensures there's enough video left to cover the audio duration.
    """
    bg_duration = get_video_duration(background_path)
    
    # If background is shorter than audio, we'll loop it, so start can be anywhere
    if bg_duration <= audio_duration:
        # Start anywhere in the video
        max_start = bg_duration - 1.0  # Leave at least 1 second
        max_start = max(0, max_start)
        start_time = random.uniform(0, max_start)
        print(f"Background duration: {bg_duration:.2f}s (will loop), starting at: {start_time:.2f}s")
    else:
        # Background is longer - pick a random start that leaves enough video
        max_start = bg_duration - audio_duration
        max_start = max(0, max_start)
        start_time = random.uniform(0, max_start)
        print(f"Background duration: {bg_duration:.2f}s, starting at: {start_time:.2f}s")
    
    return start_time


def render_video(background_path, voice_path, captions_ass_path, output_path, duration, start_time=0.0):
    """Render final video using FFmpeg with ASS subtitles (supports animations)."""
    # Use ASS file which already contains styling and animations
    # ASS format supports karaoke effects and move animations for bouncing
    
    # Get absolute path and escape it properly for FFmpeg filter
    abs_captions_path = os.path.abspath(captions_ass_path)
    # For ass filter with paths containing spaces, we need to escape:
    # - Colons (:) -> \:
    # - Backslashes (\) -> \\
    # - Spaces and special chars need the path to be single-quoted in the filter
    escaped_path = abs_captions_path.replace("\\", "\\\\").replace(":", "\\:")
    # Wrap in single quotes for FFmpeg filter (handles spaces)
    quoted_path = f"'{escaped_path}'"
    
    dur = float(duration)

    # Base video FX:
    # - Cover-fit to 1080x1920
    # - Subtle zoom (scale up then crop back)
    # - Tiny upward drift (crop y expression uses t)
    # - Burn-in captions
    base_v = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "setpts=PTS-STARTPTS,"
        "scale=iw*1.06:ih*1.06,"
        f"crop=1080:1920:x=(iw-1080)/2:y=(ih-1920)/2 - (ih-1920)*0.05*(t/{dur}),"
        f"subtitles={quoted_path}"
    )

    # Audio FX (very subtle):
    # - A tiny pop + whoosh at the start to increase perceived "hook"
    # - Voice remains dominant
    af = (
        "[1:a]volume=1.0[voice];"
        "sine=f=950:d=0.05,afade=t=in:d=0.005,afade=t=out:st=0.03:d=0.02,volume=0.10[pop];"
        "anoisesrc=d=0.22:c=pink:r=44100,highpass=f=500,lowpass=f=7000,"
        "afade=t=in:d=0.02,afade=t=out:st=0.14:d=0.08,volume=0.06[whoosh];"
        "[voice][pop][whoosh]amix=inputs=3:duration=first:dropout_transition=0[aout]"
    )

    # FFmpeg command
    # Use -ss before -i to seek to start_time (faster, more accurate)

    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-ss", str(start_time),  # Start at random point in background
        "-stream_loop", "-1",  # Loop background infinitely
        "-i", background_path,  # Background video (may have audio - we'll ignore it)
        "-i", voice_path,  # Audio (voice.mp3)
    ]

    # Progress bar (code-drawn) "slide away" animation:
    # User-visible and reliable: a full-width green bar that slowly moves off-screen.
    bar_h = 18
    bar_y_start = 0
    bar_thickness = 10
    p = f"min(1\\,t/{dur})"

    bar_graph = (
        f"color=c=black@0.0:s=1080x{bar_h}:d={dur},format=rgba,"
        f"drawbox=x=0:y={(bar_h-bar_thickness)//2}:w=iw:h={bar_thickness}:color=black@0.35:t=fill:replace=1,"
        f"drawbox=x=0:y={(bar_h-bar_thickness)//2}:w=iw:h={bar_thickness}:color=lime@0.85:t=fill:replace=1"
    )

    filter_complex = (
        f"[0:v]{base_v}[base];"
        f"{bar_graph}[bar];"
        # Slide the bar to the right so it's fully gone by the end (x from 0 -> 1080)
        f"[base][bar]overlay=x=(W*{p}):y={bar_y_start}:shortest=1[vout];"
        f"{af}"
    )

    cmd += [
        "-filter_complex",
        filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",  # Stop at shortest input (audio length)
        "-t", str(duration),  # Explicitly set duration
        output_path,
    ]
    
    print("Rendering video (this may take a moment)...")
    print(f"DEBUG: ASS file path: {abs_captions_path}")
    print(f"DEBUG: Filter: ass={escaped_path}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Print any subtitle-related messages
        stderr_lines = result.stderr.split('\n')
        for line in stderr_lines:
            if 'ass' in line.lower() or 'subtitle' in line.lower() or 'libass' in line.lower():
                print(f"FFmpeg: {line}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error:")
        print(e.stderr)
        sys.exit(1)


def main():
    check_ffmpeg()
    
    if not os.path.exists(VOICE_MP3):
        print("❌ Missing output/voice.mp3. Run: python scripts/tts.py first.")
        sys.exit(1)
    
    if not os.path.exists(CAPTIONS_ASS):
        print("❌ Missing output/captions.ass. Run: python scripts/captions_bounce.py first.")
        sys.exit(1)
    
    # Pick background
    background_path = pick_background()
    
    # Get audio duration
    duration = get_audio_duration(VOICE_MP3)
    print(f"Audio duration: {duration:.2f} seconds")
    
    # Get random start time in background video
    start_time = get_random_start_time(background_path, duration)
    
    # Render video
    os.makedirs(os.path.dirname(OUT_MP4), exist_ok=True)
    render_video(background_path, VOICE_MP3, CAPTIONS_ASS, OUT_MP4, duration, start_time)
    
    print(f"✅ Saved video to: {OUT_MP4}")
    print(f"   Resolution: 1080x1920 (9:16 vertical)")
    print(f"   Duration: {duration:.2f} seconds")


if __name__ == "__main__":
    main()
