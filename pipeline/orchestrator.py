"""Orchestrator — drive a job through the pipeline state machine.

Implements the flow from STRATEGY.md §4. Stages run in order; each is idempotent
(skipped when already done) so reruns resume failed steps without restarting.
Two human gates park the job:

  idea -> angle -> [ANGLE GATE] -> script -> similarity_guard
       -> assets -> voice -> captions -> assemble -> metadata -> thumbnail
       -> [PUBLISH GATE] -> upload

The similarity guard can bounce the script back for regeneration (up to
MAX_REGEN attempts) with a "make it different" nudge.
"""
from __future__ import annotations

from .config import Config
from .job import (Job, STATUS_ACTIVE, STATUS_AWAITING_ANGLE, STATUS_AWAITING_CLIP,
                  STATUS_AWAITING_PUBLISH, STATUS_DONE, STATUS_FAILED)
from .stages.base import SimilarityTooHigh
from .stages.clip import IngestStage, TranscribeStage, HighlightStage
from .stages.clip_render import (CutReframeStage, ClipCaptionsStage,
                                 ClipAssembleStage, ClipMetadataStage, ClipThumbnailStage)
from .stages.idea import IdeaStage
from .stages.angle import AngleStage
from .stages.script import ScriptStage
from .stages.similarity_guard import SimilarityGuardStage
from .stages.assets import AssetsStage
from .stages.voice import VoiceStage
from .stages.captions import CaptionsStage
from .stages.assemble import AssembleStage
from .stages.metadata import MetadataStage
from .stages.thumbnail import ThumbnailStage
from .stages.upload import UploadStage

MAX_REGEN = 3

# (gate_before, stage). A gate name parks the job until that gate is approved.
PLAN = [
    (None, IdeaStage()),
    (None, AngleStage()),
    ("angle", ScriptStage()),
    (None, SimilarityGuardStage()),
    (None, AssetsStage()),
    (None, VoiceStage()),
    (None, CaptionsStage()),
    (None, AssembleStage()),
    (None, MetadataStage()),
    (None, ThumbnailStage()),
    ("publish", UploadStage()),
]

# Clip mode (STRATEGY §8) — SOURCE analysis plan: find + propose clips, park at
# the clip-selection gate. (The per-clip render plan is built on top separately.)
CLIP_SOURCE_PLAN = [
    (None, IngestStage()),
    (None, TranscribeStage()),
    (None, HighlightStage()),
    ("clip", None),   # terminal gate: human approves which clips to render
]

_GATE_STATUS = {
    "angle": STATUS_AWAITING_ANGLE,
    "publish": STATUS_AWAITING_PUBLISH,
    "clip": STATUS_AWAITING_CLIP,
}

# Clip mode — RENDER plan: one approved segment → a vertical Short. Reuses
# AssetsStage (caption style), ThumbnailStage, UploadStage from the original flow.
CLIP_RENDER_PLAN = [
    (None, AssetsStage()),
    (None, CutReframeStage()),
    (None, ClipCaptionsStage()),
    (None, ClipAssembleStage()),
    (None, ClipMetadataStage()),
    (None, ClipThumbnailStage()),
    ("publish", UploadStage()),
]

_PLANS = {"clip_source": CLIP_SOURCE_PLAN, "clip": CLIP_RENDER_PLAN}


def _plan_for(job: Job):
    return _PLANS.get(getattr(job, "mode", "original"), PLAN)


def run_job(job: Job, cfg: Config, *, force: bool = False, stop_before_upload: bool = False) -> str:
    """Advance `job` as far as it can go. Returns the resulting job.status."""
    for gate, stage in _plan_for(job):
        if gate and not job.gate_approved(gate):
            job.status = _GATE_STATUS[gate]
            job.save()
            return job.status

        if stage is None:   # gate-only (terminal) entry
            continue

        if stop_before_upload and stage.name == "upload":
            job.status = STATUS_AWAITING_PUBLISH if not job.gate_approved("publish") else STATUS_ACTIVE
            job.save()
            return job.status

        if stage.done(job) and not force:
            continue

        try:
            _run_stage(job, cfg, stage)
        except SimilarityTooHigh:
            if not _regenerate(job, cfg):
                job.status = STATUS_FAILED
                job.error = "similarity guard could not produce a distinct script"
                job.save()
                return job.status
        except Exception as e:  # noqa: BLE001 - record and stop; rerun resumes here
            job.status = STATUS_FAILED
            job.error = f"{stage.name}: {e}"
            job.log(stage.name, f"FAILED: {e}")
            job.save()
            return job.status

    job.status = STATUS_DONE
    job.save()
    return job.status


def _run_stage(job: Job, cfg: Config, stage) -> None:
    job.status = STATUS_ACTIVE
    print(f"  ▶ {stage.name}")
    stage.run(job, cfg)
    job.save()


def _regenerate(job: Job, cfg: Config) -> bool:
    """Clear the script + guard outputs and re-run with a nudge, up to MAX_REGEN."""
    attempts = job.data.get("regen_count", 0)
    if attempts >= MAX_REGEN:
        return False
    job.data["regen_count"] = attempts + 1
    job.data["_regen_nudge"] = (
        "A previous version was too similar to an existing video in the catalog. "
        "Take a clearly different angle and wording — change the structure, the examples "
        "and the opening so it is genuinely distinct."
    )
    job.data.pop("script", None)
    job.data.pop("similarity", None)
    job.log("similarity_guard", f"regenerating script (attempt {attempts + 1}/{MAX_REGEN})")
    job.save()

    ScriptStage().run(job, cfg)
    job.save()
    try:
        SimilarityGuardStage().run(job, cfg)
        job.save()
        return True
    except SimilarityTooHigh:
        return _regenerate(job, cfg)
