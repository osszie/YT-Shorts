"""Script stage — write the spoken VO to defend the approved angle.

Thesis-driven and, for factual niches, grounded in real sources (STRATEGY.md §2:
specificity reads as researched, and keeps it true). The script DEFENDS the
angle using the chosen format's skeleton. A regen nudge is injected when the
similarity guard sent us back to make the script genuinely different.
"""
from __future__ import annotations

import re

from .. import llm
from ..config import Config
from ..job import Job
from .base import Stage


def _word_count(s: str) -> int:
    return len(re.findall(r"\S+", s or ""))


class ScriptStage(Stage):
    name = "script"

    def done(self, job: Job) -> bool:
        return bool(job.data.get("script"))

    def run(self, job: Job, cfg: Config) -> None:
        subject = job.data["subject"]
        angle = job.data["angle"]
        fmt = cfg.fmt(job.data["format"])
        scfg = cfg.niche.get("script", {})
        lo, hi = scfg.get("target_words", [110, 150])
        perspective = scfg.get("perspective", "")
        grounding = bool(scfg.get("grounding"))
        nudge = job.data.pop("_regen_nudge", "")

        script, sources = "", []
        if llm.available():
            prompt = (
                f"Write the spoken voiceover for a {lo}-{hi} word YouTube Short.\n"
                f"SUBJECT: {subject}\n"
                f"ANGLE (the thesis to argue, do not contradict it): {angle}\n"
                f"FORMAT — {fmt['name']}: {fmt['structure']}\n"
                f"VOICE: {perspective}\n\n"
                "Rules: open with a 1-line hook that stops the scroll; be specific and true; "
                "use concrete numbers/names where possible; no fluff; end with a short line "
                "that invites a comment. Output ONLY the spoken words (no labels, no stage "
                "directions, no markdown)."
            )
            if nudge:
                prompt += f"\n\nIMPORTANT: {nudge}"
            try:
                if grounding:
                    script, sources = llm.generate_grounded(prompt)
                else:
                    script = llm.generate_text(prompt)
            except Exception as e:
                job.log(self.name, f"llm script failed ({e}); using fallback")

        if not script.strip():
            script = self._fallback(subject, angle, fmt)

        script = script.strip()
        job.data["script"] = script
        job.data["sources"] = sources
        job.data["script_words"] = _word_count(script)
        job.mark_stage(self.name, f"{_word_count(script)} words, {len(sources)} sources"
                       + (" (grounded)" if grounding else ""))

    @staticmethod
    def _fallback(subject: str, angle: str, fmt: dict) -> str:
        return (
            f"You've seen {subject} a hundred times and never thought twice about it. "
            f"But here's the thing: {angle} "
            f"Most people assume there's nothing to it — there is. "
            f"Once you know what to look for, you can't unsee it. "
            f"What everyday thing do you want explained next?"
        )
