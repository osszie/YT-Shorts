#!/usr/bin/env python3
"""
Phase 4: YouTube Upload Agent (Entry Point)
Main script for uploading videos to YouTube with dry-run support.
"""

import os
import sys
import pathlib
from dotenv import load_dotenv

# Add scripts directory to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from youtube.validate import validate_all, print_validation_report
from youtube.metadata import build_metadata, print_metadata_preview
from youtube.auth import get_youtube_client
from youtube.upload import upload_video


def main():
    """Main entry point for YouTube upload agent."""
    # Load environment variables
    project_root = pathlib.Path(__file__).resolve().parents[1]
    env_path = project_root / '.env'
    load_dotenv(dotenv_path=env_path)
    
    print("\n" + "=" * 60)
    print("YOUTUBE UPLOAD AGENT - Phase 4")
    print("=" * 60)
    print(f"Project root: {project_root}")
    print(f"Dry run mode: {os.getenv('YOUTUBE_DRY_RUN', 'true')}")
    print("=" * 60 + "\n")
    
    # Step 1: Validation
    print("Step 1: Validating prerequisites...")
    all_valid, results = validate_all(project_root)
    print_validation_report(results)
    
    if not all_valid:
        print("❌ Validation failed. Please fix the errors above and try again.")
        sys.exit(1)
    
    # Step 2: Build metadata
    print("Step 2: Building metadata from script.json...")
    try:
        metadata = build_metadata(project_root)
        print_metadata_preview(metadata)
    except Exception as e:
        print(f"❌ Failed to build metadata: {e}")
        sys.exit(1)
    
    # Step 3: Authenticate
    print("Step 3: Authenticating with YouTube API...")
    try:
        youtube_client = get_youtube_client(project_root)
        print("✅ Authentication successful!\n")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        sys.exit(1)
    
    # Step 4: Upload (or dry run)
    video_path = project_root / 'output' / 'final.mp4'
    dry_run = os.getenv('YOUTUBE_DRY_RUN', 'true').lower() == 'true'
    
    print("Step 4: Processing upload...")
    try:
        response = upload_video(
            video_path=video_path,
            metadata=metadata,
            youtube_client=youtube_client,
            dry_run=dry_run
        )
        
        if dry_run:
            print("\n" + "=" * 60)
            print("DRY RUN COMPLETE")
            print("=" * 60)
            print("✅ All checks passed. Upload logic is ready.")
            print("\nTo enable actual uploads:")
            print("  1. Set YOUTUBE_DRY_RUN=false in .env")
            print("  2. Run this script again")
            print("=" * 60 + "\n")
        else:
            if response and 'id' in response:
                print("\n" + "=" * 60)
                print("UPLOAD COMPLETE")
                print("=" * 60)
                print(f"✅ Video uploaded successfully!")
                print(f"   Video ID: {response['id']}")
                print(f"   URL: https://www.youtube.com/watch?v={response['id']}")
                print("\nNext steps:")
                print("  - Check video in YouTube Studio")
                print("  - Adjust privacy settings if needed")
                print("  - Add thumbnail or make other edits")
                print("=" * 60 + "\n")
            else:
                print("❌ Upload completed but no video ID returned")
                sys.exit(1)
                
    except Exception as e:
        print(f"\n❌ Upload failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
