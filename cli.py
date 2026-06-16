#!/usr/bin/env python3
"""yt-shorts pipeline CLI.

Realizes "the dial" from STRATEGY.md §2: generation is automated; humans steer at
two batched gates only. Typical weekly loop:

  python cli.py new --count 20            # create jobs, auto-run to the ANGLE gate
  python cli.py angles                    # review proposed angles (batched)
  python cli.py approve-angle <id> --pick 2
  python cli.py run --all                 # script -> ... -> metadata, park at PUBLISH gate
  python cli.py publish-queue             # review finished videos (batched)
  python cli.py approve-publish <id>      # approve, then upload (dry-run by default)

Everything between the gates runs untouched.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

from pipeline.config import DEFAULT_NICHE, list_niches, load_config
from pipeline.job import (Job, all_jobs, STATUS_AWAITING_ANGLE, STATUS_AWAITING_CLIP,
                          STATUS_AWAITING_PUBLISH, STATUS_DONE, STATUS_FAILED,
                          STATUS_REJECTED)
from pipeline.orchestrator import run_job


def _cfg_for(job: Job):
    return load_config(job.niche)


def _short(text: str, n: int = 60) -> str:
    text = (text or "").replace("\n", " ")
    return text if len(text) <= n else text[: n - 1] + "…"


# --- commands -------------------------------------------------------------

def cmd_new(args) -> int:
    from pipeline.stages.idea import generate_subjects
    from pipeline.job import recent_subjects

    cfg = load_config(args.niche)
    print(f"Creating {args.count} job(s) for niche '{cfg.niche_id}', running to the ANGLE gate...\n")

    # Bulk-generate the batch's subjects in ONE call (free-tier friendly), then
    # pre-seed each job so the per-job idea stage is skipped. If it fails (e.g.
    # rate limit), fall back to per-job idea generation.
    seeds_meta: list[tuple[str, str]] = []
    try:
        seeds_meta = generate_subjects(cfg, args.count, recent_subjects())
    except Exception as e:  # noqa: BLE001
        print(f"  (bulk idea generation unavailable: {str(e)[:80]}; using per-job ideas)\n")

    for i in range(args.count):
        job = Job.create(cfg.niche_id)
        if i < len(seeds_meta):
            subject, domain = seeds_meta[i]
            job.data["subject"] = subject
            job.data["lens_domain"] = domain
            job.mark_stage("idea", f"subject='{subject}' (bulk)")
            job.save()
        print(f"[{i + 1}/{args.count}] {job.id}")
        status = run_job(job, cfg, stop_before_upload=True)
        sub = job.data.get("subject", "?")
        print(f"    → {status}: {_short(sub)}\n")
    print("Done. Review angles with:  python cli.py angles")
    return 0


def cmd_run(args) -> int:
    jobs = _select(args)
    if not jobs:
        print("No matching jobs.")
        return 1
    for job in jobs:
        cfg = _cfg_for(job)
        print(f"\n=== {job.id} ({job.niche}) ===")
        status = run_job(job, cfg, force=args.force, stop_before_upload=not args.with_upload)
        print(f"→ {status}")
    return 0


def cmd_angles(args) -> int:
    awaiting = [j for j in all_jobs() if j.status == STATUS_AWAITING_ANGLE]
    if not awaiting:
        print("No jobs awaiting the angle gate.")
        return 0
    print(f"{len(awaiting)} job(s) awaiting the ANGLE gate:\n")
    for job in awaiting:
        print(f"● {job.id}  [{job.niche}]  lens={job.data.get('lens')} format={job.data.get('format')}")
        print(f"  subject: {job.data.get('subject')}")
        for idx, cand in enumerate(job.data.get("angle_candidates", []), 1):
            mark = "›" if cand == job.data.get("angle") else " "
            print(f"   {mark}{idx}. {cand}")
        print()
    print("Approve with:  python cli.py approve-angle <id> [--pick N | --edit \"...\"]")
    print("Batch-approve defaults:  python cli.py approve-angle --all")
    return 0


def cmd_approve_angle(args) -> int:
    targets = all_jobs() if args.all else [Job.load(args.job_id)]
    targets = [j for j in targets if j.status == STATUS_AWAITING_ANGLE] if args.all else targets
    if not targets:
        print("Nothing to approve.")
        return 1
    for job in targets:
        candidates = job.data.get("angle_candidates", [])
        if args.edit:
            job.data["angle"] = args.edit
        elif args.pick and 1 <= args.pick <= len(candidates):
            job.data["angle"] = candidates[args.pick - 1]
        job.approve_gate("angle", note=_short(job.data.get("angle", ""), 80))
        job.save()
        cfg = _cfg_for(job)
        print(f"✓ {job.id}: angle approved → {_short(job.data['angle'], 70)}")
        status = run_job(job, cfg, stop_before_upload=True)
        print(f"    → {status}")
    print("\nReview finished videos with:  python cli.py publish-queue")
    return 0


def cmd_publish_queue(args) -> int:
    awaiting = [j for j in all_jobs() if j.status == STATUS_AWAITING_PUBLISH]
    if not awaiting:
        print("No jobs awaiting the publish gate.")
        return 0
    print(f"{len(awaiting)} job(s) awaiting the PUBLISH gate:\n")
    for job in awaiting:
        meta = job.data.get("metadata", {})
        sim = job.data.get("similarity", {})
        print(f"● {job.id}  [{job.niche}]")
        thumb = job.data.get("thumbnail", {})
        print(f"  title:   {meta.get('title')}")
        print(f"  subject: {job.data.get('subject')}")
        print(f"  sim:     cos={sim.get('score')} (threshold {sim.get('threshold')})")
        print(f"  video:   {job.artifact('final.mp4')}")
        print(f"  thumb:   {job.artifact('thumbnail.jpg')}  headline='{thumb.get('headline','')}'")
        print()
    print("Approve with:  python cli.py approve-publish <id>   (uploads; dry-run unless YOUTUBE_DRY_RUN=false)")
    return 0


def cmd_approve_publish(args) -> int:
    targets = [j for j in all_jobs() if j.status == STATUS_AWAITING_PUBLISH] if args.all else [Job.load(args.job_id)]
    if not targets:
        print("Nothing to approve.")
        return 1
    for job in targets:
        job.approve_gate("publish")
        job.save()
        cfg = _cfg_for(job)
        print(f"✓ {job.id}: publish approved")
        status = run_job(job, cfg, force=False, stop_before_upload=False)
        print(f"    → {status}")
    return 0


def cmd_reject(args) -> int:
    job = Job.load(args.job_id)
    job.status = STATUS_REJECTED
    job.log("reject", args.reason or "")
    job.save()
    print(f"✗ {job.id} rejected.")
    return 0


def cmd_status(args) -> int:
    jobs = all_jobs()
    if not jobs:
        print("No jobs yet. Create some:  python cli.py new --count 5")
        return 0
    buckets: dict[str, int] = {}
    print(f"{'JOB':<24} {'NICHE':<16} {'STATUS':<18} {'STAGE':<16} SUBJECT")
    print("-" * 100)
    for job in jobs:
        buckets[job.status] = buckets.get(job.status, 0) + 1
        print(f"{job.id:<24} {job.niche:<16} {job.status:<18} {job.stage:<16} {_short(job.data.get('subject',''), 32)}")
    print("-" * 100)
    print("  ".join(f"{k}={v}" for k, v in sorted(buckets.items())))
    return 0


def cmd_show(args) -> int:
    import json
    job = Job.load(args.job_id)
    print(json.dumps({
        "id": job.id, "niche": job.niche, "status": job.status, "stage": job.stage,
        "error": job.error, "gates": job.gates, "data": job.data,
    }, indent=2, ensure_ascii=False))
    return 0


def cmd_clip(args) -> int:
    from pipeline.clip import download as dl

    cfg = load_config(args.niche)
    data: dict = {"want_clips": args.count}
    if dl.is_url(args.video):                       # Twitch / YouTube / etc.
        data["source_url"] = args.video
        label = args.video
    else:
        video = pathlib.Path(args.video).expanduser()
        if not video.exists():
            print(f"❌ video not found: {video}")
            return 1
        data["source_path"] = str(video.resolve())
        label = video.name
    if args.section:
        data["source_section"] = args.section
    job = Job.create(cfg.niche_id, mode="clip_source", data=data)
    win = f" [{args.section}]" if args.section else ""
    print(f"Analysing {label}{win} for up to {args.count} clip(s)…  job {job.id}\n")
    status = run_job(job, cfg)
    if status == STATUS_AWAITING_CLIP:
        n = len(job.data.get("clips_proposed", []))
        print(f"→ proposed {n} clip(s). Review:  python cli.py clips")
    else:
        print(f"→ {status}: {job.error or ''}")
    return 0


def cmd_clips(args) -> int:
    awaiting = [j for j in all_jobs() if j.mode == "clip_source" and j.status == STATUS_AWAITING_CLIP]
    if not awaiting:
        print("No source videos awaiting the clip gate.")
        return 0
    print(f"{len(awaiting)} source video(s) awaiting the CLIP gate:\n")
    for job in awaiting:
        src = job.data.get("source", {})
        name = pathlib.Path(src.get("path", "?")).name
        print(f"● {job.id}  [{name}, {src.get('duration', '?')}s]")
        for i, c in enumerate(job.data.get("clips_proposed", []), 1):
            print(f"   {i}. [{c['start']:.0f}–{c['end']:.0f}s] score={c['score']:.2f}  {_short(c['hook'], 60)}")
        print()
    print("Approve with:  python cli.py approve-clip <id> [--pick 1,3]")
    return 0


def cmd_approve_clip(args) -> int:
    job = Job.load(args.job_id)
    proposed = job.data.get("clips_proposed", [])
    if args.pick:
        idxs = [int(x) for x in args.pick.replace(" ", "").split(",") if x]
        chosen = [proposed[i - 1] for i in idxs if 1 <= i <= len(proposed)]
    else:
        chosen = proposed
    if not chosen:
        print("Nothing to approve.")
        return 1
    cfg = _cfg_for(job)
    # Slice the source transcript per clip (clip-relative timings) so each render
    # job can caption itself without re-transcribing.
    import json
    words_all = []
    tpath = job.artifact("transcript.json")
    if tpath.exists():
        with open(tpath, "r", encoding="utf-8") as f:
            words_all = json.load(f).get("words", [])

    created = []
    for c in chosen:
        s, e = c["start"], c["end"]
        wslice = [{"word": w["word"], "start": round(w["start"] - s, 3), "end": round(w["end"] - s, 3)}
                  for w in words_all if s <= w["start"] < e]
        child = Job.create(cfg.niche_id, mode="clip", data={
            "source_path": job.data["source"]["path"], "clip": c,
            "words": wslice, "clip_text": " ".join(w["word"] for w in wslice),
            "from_source": job.id})
        created.append(child.id)
    job.approve_gate("clip", note=f"{len(created)} clips")
    job.data["clips_created"] = created
    job.save()
    run_job(job, cfg)  # source job → done
    print(f"✓ {job.id}: created {len(created)} clip render job(s).")
    print("  Render them:  python cli.py run --all   then  python cli.py publish-queue")
    return 0


def cmd_doctor(args) -> int:
    from pipeline import doctor
    groups = doctor.run_checks(probe=getattr(args, "probe", False))
    icon = {doctor.OK: "✓", doctor.WARN: "!", doctor.FAIL: "✗"}
    for group, checks in groups.items():
        print(f"\n{group}:")
        for name, status, detail in checks:
            print(f"  {icon[status]} {name}: {detail}")
    s = doctor.summarize(groups)
    print("\n" + "=" * 60)
    if s["ready"]:
        print("✓ Spine ready — you can generate + assemble videos (dry-run upload).")
    else:
        print(f"✗ Blocked (must fix): {', '.join(s['fails'])}")
    if s["warns"]:
        print(f"! Optional / limited: {', '.join(s['warns'])}")
    return 0 if s["ready"] else 1


def cmd_niches(args) -> int:
    print("Available niches (default: %s):" % DEFAULT_NICHE)
    for n in list_niches():
        cfg = load_config(n)
        marker = "*" if n == DEFAULT_NICHE else " "
        print(f" {marker} {n:<16} {cfg.niche.get('name','')}")
    return 0


# --- selection helper -----------------------------------------------------

def _select(args) -> list[Job]:
    if getattr(args, "all", False):
        statuses = {STATUS_AWAITING_ANGLE, STATUS_AWAITING_PUBLISH, STATUS_FAILED, "active"}
        return [j for j in all_jobs() if j.status in statuses]
    if getattr(args, "job_id", None):
        return [Job.load(args.job_id)]
    return []


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="yt-shorts originality pipeline")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("new", help="create jobs and run to the angle gate")
    s.add_argument("--niche", default=DEFAULT_NICHE)
    s.add_argument("--count", type=int, default=1)
    s.set_defaults(func=cmd_new)

    s = sub.add_parser("run", help="advance job(s) through automated stages")
    s.add_argument("job_id", nargs="?")
    s.add_argument("--all", action="store_true")
    s.add_argument("--force", action="store_true", help="rerun stages even if done")
    s.add_argument("--with-upload", action="store_true", help="do not stop before upload")
    s.set_defaults(func=cmd_run)

    sub.add_parser("angles", help="list jobs awaiting the angle gate").set_defaults(func=cmd_angles)

    s = sub.add_parser("approve-angle", help="approve/pick an angle (batched gate 1)")
    s.add_argument("job_id", nargs="?")
    s.add_argument("--all", action="store_true", help="approve all awaiting (uses default pick)")
    s.add_argument("--pick", type=int, help="choose candidate N")
    s.add_argument("--edit", help="replace the angle with custom text")
    s.set_defaults(func=cmd_approve_angle)

    sub.add_parser("publish-queue", help="list jobs awaiting the publish gate").set_defaults(func=cmd_publish_queue)

    s = sub.add_parser("approve-publish", help="approve publish + upload (batched gate 2)")
    s.add_argument("job_id", nargs="?")
    s.add_argument("--all", action="store_true")
    s.set_defaults(func=cmd_approve_publish)

    s = sub.add_parser("reject", help="reject a job")
    s.add_argument("job_id")
    s.add_argument("--reason", default="")
    s.set_defaults(func=cmd_reject)

    s = sub.add_parser("show", help="dump a job record as JSON")
    s.add_argument("job_id")
    s.set_defaults(func=cmd_show)

    s = sub.add_parser("clip", help="analyse a local video OR a URL (Twitch/YouTube) and propose Shorts clips")
    s.add_argument("video", help="local video path OR a URL (Twitch VOD/clip, YouTube, …)")
    s.add_argument("--niche", default=DEFAULT_NICHE)
    s.add_argument("--count", type=int, default=3, help="how many clips to propose")
    s.add_argument("--section", help="only this window of a long source, e.g. 600-1200 or 00:10:00-00:20:00")
    s.set_defaults(func=cmd_clip)

    sub.add_parser("clips", help="list source videos awaiting the clip gate").set_defaults(func=cmd_clips)

    s = sub.add_parser("approve-clip", help="approve clips → create per-clip render jobs")
    s.add_argument("job_id")
    s.add_argument("--pick", help="comma-separated clip numbers, e.g. 1,3 (default: all)")
    s.set_defaults(func=cmd_approve_clip)

    sub.add_parser("status", help="overview of all jobs").set_defaults(func=cmd_status)
    sub.add_parser("niches", help="list available niches").set_defaults(func=cmd_niches)
    s = sub.add_parser("doctor", help="check environment readiness")
    s.add_argument("--probe", action="store_true", help="also make a live Gemini call to check the key + quota")
    s.set_defaults(func=cmd_doctor)
    return p


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
