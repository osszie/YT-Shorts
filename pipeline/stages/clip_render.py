"""Clip-mode RENDER stages: turn one approved segment into a vertical Short.

cut+reframe (face-aware 9:16) → captions (from the transcript slice, no
re-transcribe) → assemble (burn captions on the reframed clip) → metadata.
Thumbnail / publish gate / upload are reused from the original pipeline.
"""
from __future__ import annotations

import json
import os
import subprocess

from ..clip import reframe as rf
from ..config import Config
from ..job import Job
from ..media import captions, probe, remotion, thumbnail
from .base import Stage


class CutReframeStage(Stage):
    name = "cut_reframe"

    def done(self, job: Job) -> bool:
        return job.artifact("segment.mp4").exists()

    def run(self, job: Job, cfg: Config) -> None:
        clip = job.data["clip"]
        seg = str(job.artifact("segment.mp4"))
        rf.cut(job.data["source_path"], clip["start"], clip["end"], seg)
        w, h = probe.dimensions(seg)
        track = rf.face_track(seg)                       # smooth per-frame follow
        job.data["clip_dims"] = {"w": w, "h": h}
        job.data["face_track"] = track
        job.data["video_duration"] = round(clip["end"] - clip["start"], 2)
        job.data["reframe"] = {"face_tracked": bool(track), "points": len(track)}
        job.mark_stage(self.name,
                       f"cut {clip['start']:.0f}-{clip['end']:.0f}s, {len(track)} face points")


class ClipCaptionsStage(Stage):
    name = "captions"

    def done(self, job: Job) -> bool:
        # Both artifacts are required: JSON feeds the Remotion engine, ASS feeds
        # the FFmpeg fallback — requiring both keeps interrupted runs resumable
        # (same fix as the original-mode CaptionsStage).
        return job.artifact("captions.json").exists() and job.artifact("captions.ass").exists()

    def run(self, job: Job, cfg: Config) -> None:
        words = job.data.get("words", [])
        total = float(job.data.get("video_duration")
                      or probe.duration_seconds(str(job.artifact("segment.mp4"))))
        track = captions.build_track_from_words(words, total) if words else []
        with open(job.artifact("captions.json"), "w", encoding="utf-8") as f:
            json.dump({"duration": total, "chunks": track}, f, ensure_ascii=False)
        captions.write_ass(track, str(job.artifact("captions.ass")), job.data["caption_style"])
        job.mark_stage(self.name, f"{len(track)} caption chunks")


class ClipAssembleStage(Stage):
    name = "assemble"

    def done(self, job: Job) -> bool:
        return job.artifact("final.mp4").exists()

    def run(self, job: Job, cfg: Config) -> None:
        probe.require("ffmpeg")
        seg = str(job.artifact("segment.mp4"))
        out = str(job.artifact("final.mp4"))
        duration = float(job.data.get("video_duration") or probe.duration_seconds(seg))
        style = job.data["caption_style"]
        dims = job.data.get("clip_dims") or {"w": 1920, "h": 1080}
        face = job.data.get("face_track", [])
        with open(job.artifact("captions.json"), "r", encoding="utf-8") as f:
            track = json.load(f)["chunks"]

        # Default to Remotion: dynamic per-frame pan following the speaker +
        # karaoke captions. Fall back to an FFmpeg static face-centered crop +
        # ASS caption burn when Remotion isn't available.
        engine = os.getenv("RENDER_ENGINE", "remotion").lower()
        if engine == "remotion" and remotion.available():
            try:
                remotion.render_clip(job_dir=job.dir, video_src=seg,
                                     source_w=dims["w"], source_h=dims["h"], face_track=face,
                                     caption_track=track, duration=duration, style=style, out_mp4=out)
                job.data["render_engine"] = "remotion"
                job.data["video_duration"] = round(duration, 2)
                job.mark_stage(self.name, "final.mp4 (clip, remotion dynamic-pan)")
                return
            except remotion.RemotionUnavailable as e:
                job.log(self.name, f"remotion unavailable ({e}); falling back to ffmpeg")

        reframed = str(job.artifact("reframed.mp4"))
        rf.static_crop(seg, reframed, rf.median_cx(face))
        ass = os.path.abspath(str(job.artifact("captions.ass")))
        escaped = ass.replace("\\", "\\\\").replace(":", "\\:")
        cmd = ["ffmpeg", "-y", "-i", reframed, "-vf", f"subtitles='{escaped}'",
               "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "copy", out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"clip assemble (caption burn) failed:\n{r.stderr[-600:]}")
        job.data["render_engine"] = "ffmpeg"
        job.data["video_duration"] = round(probe.duration_seconds(out), 2)
        job.mark_stage(self.name, "final.mp4 (clip, ffmpeg static-crop)")


class ClipThumbnailStage(Stage):
    name = "thumbnail"

    def done(self, job: Job) -> bool:
        return job.artifact("thumbnail.jpg").exists()

    def run(self, job: Job, cfg: Config) -> None:
        # Clean thumbnail: a frame from the clip, no hook/text overlay.
        ts = max(0.5, float(job.data.get("video_duration", 4.0)) * 0.3)
        thumbnail.render(str(job.artifact("final.mp4")), str(job.artifact("thumbnail.jpg")),
                         lines=[], style=job.data["caption_style"], timestamp=ts)
        job.data["thumbnail"] = {"clean": True}
        job.mark_stage(self.name, "thumbnail.jpg (clean frame)")


class ClipMetadataStage(Stage):
    name = "metadata"

    def done(self, job: Job) -> bool:
        return bool(job.data.get("metadata"))

    def run(self, job: Job, cfg: Config) -> None:
        clip_title = (job.data.get("clip", {}).get("title") or "").strip()
        text = (job.data.get("clip_text") or "").strip()
        meta_cfg = cfg.niche.get("metadata", {})
        base_tags = meta_cfg.get("base_hashtags", ["#shorts"])
        category = str(meta_cfg.get("category_id", "24"))

        # No hook. Titling is the user's choice (CLIP_TITLE_MODE):
        #   auto  → a plain descriptive title from the highlight step (default)
        #   blank → empty title to fill in yourself at the publish gate
        mode = os.getenv("CLIP_TITLE_MODE", "auto").lower()
        title = "" if mode == "blank" else (clip_title or "Clip")

        desc = text
        if len(desc) > 180:
            desc = desc[:180].rsplit(" ", 1)[0] + "…"
        hashtags = " ".join(dict.fromkeys(base_tags))
        job.data["metadata"] = {
            "title": title[:100],
            "description": (f"{desc}\n\n{hashtags}" if desc else hashtags),
            "tags": [t.lstrip("#") for t in base_tags][:15],
            "category_id": category,
        }
        job.mark_stage(self.name, f"title='{title[:60]}' ({mode})")
