"""Upload stage — push the approved video to YouTube (scheduled, dry-run safe).

Runs only after the PUBLISH GATE is approved. Defaults to dry-run unless
YOUTUBE_DRY_RUN=false, so an accidental run never publishes. Builds the API
payload straight from the job's metadata; supports scheduled publish via
SCHEDULE_HOURS.
"""
from __future__ import annotations

import datetime
import os

from .. import ROOT
from ..config import Config
from ..job import Job
from .base import Stage


class UploadStage(Stage):
    name = "upload"

    def done(self, job: Job) -> bool:
        return bool(job.data.get("upload", {}).get("video_id"))

    def run(self, job: Job, cfg: Config) -> None:
        from ..youtube.auth import get_youtube_client
        from ..youtube.upload import upload_video

        meta = job.data["metadata"]
        privacy = os.getenv("YOUTUBE_PRIVACY_STATUS", "private")
        made_for_kids = os.getenv("YOUTUBE_MADE_FOR_KIDS", "false").lower() == "true"
        dry_run = os.getenv("YOUTUBE_DRY_RUN", "true").lower() == "true"

        body = {
            "snippet": {
                "title": meta["title"],
                "description": meta["description"],
                "tags": meta.get("tags", []),
                "categoryId": meta.get("category_id", "27"),
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": made_for_kids,
            },
        }

        # Optional scheduled publish.
        schedule_hours = os.getenv("SCHEDULE_HOURS")
        if schedule_hours:
            publish_at = datetime.datetime.now(datetime.timezone.utc) + \
                datetime.timedelta(hours=float(schedule_hours))
            body["status"]["privacyStatus"] = "private"
            body["status"]["publishAt"] = publish_at.isoformat()

        client = None if dry_run else get_youtube_client(ROOT)
        resp = upload_video(job.artifact("final.mp4"), body, client, dry_run=dry_run)
        video_id = resp.get("id") if resp else None

        job.data["upload"] = {
            "video_id": video_id,
            "dry_run": dry_run,
            "privacy": body["status"]["privacyStatus"],
            "scheduled_for": body["status"].get("publishAt"),
        }

        # Set the branded custom thumbnail (best-effort: requires a verified channel).
        thumb = job.artifact("thumbnail.jpg")
        if not dry_run and video_id and thumb.exists():
            try:
                from googleapiclient.http import MediaFileUpload
                client.thumbnails().set(
                    videoId=video_id, media_body=MediaFileUpload(str(thumb)),
                ).execute()
                job.data["upload"]["thumbnail_set"] = True
            except Exception as e:  # noqa: BLE001
                job.log(self.name, f"thumbnail set failed ({e}); custom thumbnails need a verified channel")
                job.data["upload"]["thumbnail_set"] = False

        job.mark_stage(self.name, f"{'dry-run' if dry_run else 'uploaded'} id={video_id}")
