#!/usr/bin/env python3
"""
Run the full yt-shorts-agent pipeline end-to-end:
1) Generate story (Ollama) -> output/script.json
2) Generate voice (Edge TTS) -> output/voice.mp3
3) Generate auto captions (Whisper) -> output/captions.ass
4) Render video (FFmpeg) -> output/final.mp4
5) Optional: YouTube upload agent (dry-run by default)
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys
import time

try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm not available
    class tqdm:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def update(self, n=1):
            pass
        def set_description(self, desc):
            pass


ROOT = pathlib.Path(__file__).resolve().parents[1]


def run_step(name: str, argv: list[str], progress_bar: tqdm | None = None) -> None:
    if progress_bar:
        progress_bar.set_description(f"🔄 {name}")
    print("\n" + "=" * 70)
    print(f"{name}")
    print("=" * 70)
    print(" ".join(argv))
    start_time = time.time()
    subprocess.run(argv, check=True)
    elapsed = time.time() - start_time
    if progress_bar:
        progress_bar.set_description(f"✅ {name} ({elapsed:.1f}s)")
        progress_bar.update(1)


def main() -> int:
    p = argparse.ArgumentParser(description="Run all phases of yt-shorts-agent.")
    p.add_argument("--skip-agent", action="store_true", help="Skip story generation (uses existing output/script.json).")
    p.add_argument("--skip-tts", action="store_true", help="Skip TTS generation (uses existing output/voice.mp3).")
    p.add_argument("--skip-captions", action="store_true", help="Skip captions generation (uses existing output/captions.ass).")
    p.add_argument("--skip-render", action="store_true", help="Skip rendering (uses existing output/final.mp4).")

    p.add_argument("--upload", action="store_true", help="Run Phase 4 YouTube upload agent (scripts/upload_youtube.py).")
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="When used with --upload, run upload agent in dry-run mode (default: true).",
    )
    p.add_argument(
        "--no-dry-run",
        action="store_true",
        help="When used with --upload, disable dry-run (will attempt a real upload).",
    )
    args = p.parse_args()

    if args.no_dry_run:
        args.dry_run = False

    py = sys.executable
    if not py:
        print("❌ Could not determine python executable.")
        return 1

    # Count total phases to run
    total_phases = 0
    phases = []
    
    if not args.skip_agent:
        phases.append(("Phase 1: Story generation", [py, str(ROOT / "scripts" / "agent.py")]))
        total_phases += 1
    
    if not args.skip_tts:
        phases.append(("Phase 2: Voice synthesis", [py, str(ROOT / "scripts" / "tts.py")]))
        total_phases += 1
    
    if not args.skip_captions:
        phases.append(("Phase 3a: Captions (Whisper auto-captions -> ASS)", [py, str(ROOT / "scripts" / "captions_bounce.py")]))
        total_phases += 1
    
    if not args.skip_render:
        phases.append(("Phase 3b: Render video", [py, str(ROOT / "scripts" / "render.py")]))
        total_phases += 1
    
    if args.upload:
        total_phases += 1

    try:
        # Create progress bar
        with tqdm(total=total_phases, desc="🚀 Pipeline", unit="phase", ncols=100, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:
            # Run each phase
            for phase_name, phase_argv in phases:
                run_step(phase_name, phase_argv, progress_bar=pbar)
            
            # Upload phase (if requested)
            if args.upload:
                # upload_youtube.py reads YOUTUBE_DRY_RUN from env
                env = os.environ.copy()
                env["YOUTUBE_DRY_RUN"] = "true" if args.dry_run else "false"
                pbar.set_description("🔄 Phase 4: YouTube upload agent")
                print("\n" + "=" * 70)
                print("Phase 4: YouTube upload agent")
                print("=" * 70)
                print(f"YOUTUBE_DRY_RUN={env['YOUTUBE_DRY_RUN']}")
                start_time = time.time()
                subprocess.run([py, str(ROOT / "scripts" / "upload_youtube.py")], check=True, env=env)
                elapsed = time.time() - start_time
                pbar.set_description(f"✅ Phase 4: YouTube upload agent ({elapsed:.1f}s)")
                pbar.update(1)

        print("\n✅ Pipeline complete.")
        print(f"Outputs:\n- {ROOT / 'output' / 'script.json'}\n- {ROOT / 'output' / 'voice.mp3'}\n- {ROOT / 'output' / 'captions.ass'}\n- {ROOT / 'output' / 'final.mp4'}")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Step failed (exit {e.returncode}).")
        return e.returncode


if __name__ == "__main__":
    raise SystemExit(main())

