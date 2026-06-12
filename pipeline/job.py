"""The job record + state machine.

STRATEGY.md §4: "Each video = one job row with a state machine. Each stage is an
idempotent function writing to the shared job record. Gives rerun-failed-steps,
logging and error handling for free."

A job is a directory under jobs/<job_id>/ holding:
  - job.json     : the shared record (this module)
  - voice.mp3, captions.ass, final.mp4 : media artifacts written by stages

Stages read/write job.data[...] and call job.save(). Because every stage records
its own output and checks for it, reruns skip completed work and resume failed
steps without restarting the whole pipeline.
"""
from __future__ import annotations

import json
import pathlib
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any

from . import ROOT

JOBS_DIR = ROOT / "jobs"

# Ordered pipeline states. `status` is the coarse lifecycle; `stage` records the
# last completed stage so the orchestrator knows where to resume.
STATUS_ACTIVE = "active"            # mid-pipeline, no gate blocking
STATUS_AWAITING_ANGLE = "awaiting_angle"   # parked at the angle gate
STATUS_AWAITING_PUBLISH = "awaiting_publish"  # parked at the publish gate
STATUS_DONE = "done"
STATUS_FAILED = "failed"
STATUS_REJECTED = "rejected"


def _now() -> float:
    return time.time()


@dataclass
class Job:
    id: str
    niche: str
    status: str = STATUS_ACTIVE
    stage: str = "created"          # last completed stage
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    data: dict[str, Any] = field(default_factory=dict)
    gates: dict[str, Any] = field(default_factory=lambda: {
        "angle": {"approved": False},
        "publish": {"approved": False},
    })
    history: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    # --- filesystem ------------------------------------------------------
    @property
    def dir(self) -> pathlib.Path:
        return JOBS_DIR / self.id

    def artifact(self, name: str) -> pathlib.Path:
        return self.dir / name

    # --- lifecycle helpers ----------------------------------------------
    def log(self, stage: str, note: str = "") -> None:
        self.history.append({"stage": stage, "note": note, "at": _now()})

    def mark_stage(self, stage: str, note: str = "") -> None:
        self.stage = stage
        self.error = None
        self.log(stage, note)

    def gate_approved(self, name: str) -> bool:
        return bool(self.gates.get(name, {}).get("approved"))

    def approve_gate(self, name: str, by: str = "human", note: str = "") -> None:
        self.gates.setdefault(name, {})
        self.gates[name].update({"approved": True, "by": by, "at": _now(), "note": note})
        self.log(f"gate:{name}", f"approved by {by}. {note}".strip())

    # --- persistence -----------------------------------------------------
    def save(self) -> None:
        self.updated_at = _now()
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.dir / "job.json.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)
        tmp.replace(self.dir / "job.json")

    @classmethod
    def load(cls, job_id: str) -> "Job":
        path = JOBS_DIR / job_id / "job.json"
        if not path.exists():
            raise FileNotFoundError(f"No such job: {job_id}")
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return cls(**raw)

    @classmethod
    def create(cls, niche: str) -> "Job":
        job_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        job = cls(id=job_id, niche=niche)
        job.mark_stage("created")
        job.save()
        return job


def all_jobs() -> list[Job]:
    if not JOBS_DIR.exists():
        return []
    jobs = []
    for d in sorted(JOBS_DIR.iterdir()):
        if (d / "job.json").exists():
            try:
                jobs.append(Job.load(d.name))
            except Exception:
                continue
    return jobs
