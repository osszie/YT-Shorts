"""yt-shorts originality pipeline.

A modular, job-based pipeline that produces genuine per-video variation and a
real point of view, the way STRATEGY.md requires. The hard constraint driving
the whole design is YouTube's 2025 monetization policy: the thing that makes
automation easy (one template, same voice, same structure) is exactly what gets
channels demonetized. So originality is injected at generation (angle engine +
format bank + grounding + surface variation) and enforced at a gate before
publish (similarity guard + two batched human gates).
"""

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
