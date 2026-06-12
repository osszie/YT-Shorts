"""Similarity guard stage (STRATEGY.md §2, Half 2).

Embeds the finished script and compares it to the back catalog of accepted
scripts. Above the threshold it raises SimilarityTooHigh, which the orchestrator
catches to regenerate the script with a "make it different" nudge. This is the
cheap, high-value mechanism that prevents the 30-near-identical-videos pattern
that gets channels demonetized at the channel level.
"""
from __future__ import annotations

from .. import similarity
from ..config import Config
from ..job import Job
from .base import SimilarityTooHigh, Stage


class SimilarityGuardStage(Stage):
    name = "similarity_guard"

    def done(self, job: Job) -> bool:
        return bool(job.data.get("similarity", {}).get("passed"))

    def run(self, job: Job, cfg: Config) -> None:
        script = job.data["script"]
        score, similar_to = similarity.max_similarity(script)
        threshold = similarity.THRESHOLD
        job.data["similarity"] = {
            "score": round(score, 4),
            "threshold": threshold,
            "most_similar": similar_to,
            "passed": score < threshold,
        }
        if score >= threshold:
            job.log(self.name, f"REJECT cos={score:.3f} >= {threshold} (vs {similar_to})")
            raise SimilarityTooHigh(score, similar_to)

        # Remember this accepted script so future jobs are compared against it.
        similarity.remember(job.id, script)
        job.mark_stage(self.name, f"OK cos={score:.3f} < {threshold}")
