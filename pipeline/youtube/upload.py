#!/usr/bin/env python3
"""YouTube video upload with dry-run support (resumable, YouTube Data API v3)."""

import pathlib
from typing import Dict, Optional

from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


def upload_video(video_path: pathlib.Path, metadata: Dict, youtube_client,
                 dry_run: bool = True) -> Optional[Dict]:
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    if dry_run:
        print("  🧪 DRY RUN — not uploading.")
        print(f"     Title:   {metadata['snippet']['title']}")
        print(f"     Privacy: {metadata['status']['privacyStatus']}")
        print(f"     Tags:    {', '.join(metadata['snippet'].get('tags', []))}")
        return {"id": "DRY_RUN_MOCK_VIDEO_ID", "snippet": metadata["snippet"]}

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube_client.videos().insert(
        part=",".join(metadata.keys()), body=metadata, media_body=media)

    response, retry, max_retries = None, 0, 3
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"     upload {int(status.progress() * 100)}%")
            if response is not None:
                if "id" in response:
                    print(f"  ✅ uploaded: https://www.youtube.com/watch?v={response['id']}")
                    return response
                raise RuntimeError(f"Upload failed: {response}")
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504):
                retry += 1
                if retry > max_retries:
                    raise RuntimeError(f"Max retries exceeded (HTTP {e.resp.status}).")
                print(f"     retriable HTTP {e.resp.status}, retry {retry}/{max_retries}")
            else:
                raise RuntimeError(f"HTTP {e.resp.status}: {e.content.decode('utf-8')}")
    return None
