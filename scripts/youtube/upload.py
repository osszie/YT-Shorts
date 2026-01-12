#!/usr/bin/env python3
"""
YouTube video upload module with dry-run support.
Handles resumable uploads via YouTube Data API v3.
"""

import pathlib
from typing import Dict, Optional
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


def upload_video(
    video_path: pathlib.Path,
    metadata: Dict,
    youtube_client,
    dry_run: bool = True
) -> Optional[Dict]:
    """
    Upload video to YouTube or simulate upload (dry run).
    
    Args:
        video_path: Path to video file (output/final.mp4)
        metadata: Video metadata dict from metadata.py
        youtube_client: Authenticated YouTube API client
        dry_run: If True, simulate upload without actually uploading
        
    Returns:
        Response dict with videoId if successful, None if dry run
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    if dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN MODE - Upload Simulation")
        print("=" * 60)
        print(f"Video file: {video_path}")
        print(f"File size: {video_path.stat().st_size / (1024*1024):.2f} MB")
        print(f"\nMetadata that would be uploaded:")
        print(f"  Title: {metadata['snippet']['title']}")
        print(f"  Privacy: {metadata['status']['privacyStatus']}")
        print(f"  Tags: {', '.join(metadata['snippet']['tags'])}")
        print(f"\n✅ DRY RUN: Upload skipped (no video uploaded)")
        print("=" * 60 + "\n")
        
        # Return mock response
        return {
            'id': 'DRY_RUN_MOCK_VIDEO_ID',
            'snippet': {
                'title': metadata['snippet']['title'],
                'description': metadata['snippet']['description']
            }
        }
    
    # Actual upload
    print("\n" + "=" * 60)
    print("UPLOADING TO YOUTUBE")
    print("=" * 60)
    print(f"Video file: {video_path}")
    print(f"File size: {video_path.stat().st_size / (1024*1024):.2f} MB")
    print("\n⏳ Uploading... (this may take a while)")
    
    # Create media upload object with resumable upload
    media = MediaFileUpload(
        str(video_path),
        chunksize=-1,  # Use resumable upload
        resumable=True,
        mimetype='video/mp4'
    )
    
    # Prepare upload request
    insert_request = youtube_client.videos().insert(
        part=','.join(metadata.keys()),
        body=metadata,
        media_body=media
    )
    
    # Execute resumable upload
    response = None
    error = None
    retry = 0
    max_retries = 3
    
    while response is None:
        try:
            status, response = insert_request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"   Upload progress: {progress}%")
            
            if response is not None:
                if 'id' in response:
                    video_id = response['id']
                    print(f"\n✅ Upload successful!")
                    print(f"   Video ID: {video_id}")
                    print(f"   URL: https://www.youtube.com/watch?v={video_id}")
                    return response
                else:
                    raise Exception(f"Upload failed: {response}")
                    
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                error = f"Retriable HTTP {e.resp.status} error"
                retry += 1
                if retry > max_retries:
                    raise Exception(f"Max retries exceeded. {error}")
                print(f"   ⚠️  {error} - Retrying... (attempt {retry}/{max_retries})")
            else:
                error_msg = f"HTTP {e.resp.status} error: {e.content.decode('utf-8')}"
                raise Exception(error_msg)
        except Exception as e:
            raise Exception(f"Upload error: {str(e)}")
    
    return None
