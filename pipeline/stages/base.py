from __future__ import annotations

from ..config import Config
from ..job import Job


class SimilarityTooHigh(Exception):
    """Raised by the similarity guard to trigger a script regeneration."""

    def __init__(self, score: float, similar_to: str | None):
        self.score = score
        self.similar_to = similar_to
        super().__init__(f"script too similar (cos={score:.3f}) to job {similar_to}")


class Stage:
    """Base stage. Subclasses set `name` and implement run(); `done()` makes the
    stage idempotent so reruns skip completed work."""

    name: str = "stage"

    def done(self, job: Job) -> bool:
        return False

    def run(self, job: Job, cfg: Config) -> None:  # pragma: no cover - interface
        raise NotImplementedError
