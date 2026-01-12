#!/usr/bin/env python3
"""
Metadata builder for YouTube video uploads.
Builds metadata dict from script.json and environment variables.
"""

import os
import json
import pathlib
from typing import Dict


def load_script_json(script_path: pathlib.Path) -> Dict[str, str]:
    """
    Load and return script.json data.
    
    Raises:
        FileNotFoundError: If script.json doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    if not script_path.exists():
        raise FileNotFoundError(f"Script file not found: {script_path}")
    
    with open(script_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def ensure_shorts_tag(description: str) -> str:
    """
    Ensure #shorts is present in description.
    Adds it if missing.
    """
    description = description.strip()
    if '#shorts' not in description.lower():
        if description:
            description += '\n\n#shorts'
        else:
            description = '#shorts'
    return description


def truncate_title(title: str, max_length: int = 100) -> str:
    """
    Truncate title to max_length characters.
    YouTube title limit is 100 characters.
    """
    if len(title) <= max_length:
        return title
    return title[:max_length - 3] + '...'


def build_metadata(project_root: pathlib.Path) -> Dict:
    """
    Build YouTube video metadata from script.json and environment variables.
    
    Returns:
        Dictionary ready for YouTube videos.insert API call
    """
    script_path = project_root / 'output' / 'script.json'
    script_data = load_script_json(script_path)
    
    # Get environment variables
    category_id = os.getenv('YOUTUBE_CATEGORY_ID', '24')  # Entertainment default
    privacy_status = os.getenv('YOUTUBE_PRIVACY_STATUS', 'private')
    made_for_kids = os.getenv('YOUTUBE_MADE_FOR_KIDS', 'false').lower() == 'true'
    tags_str = os.getenv('YOUTUBE_TAGS', 'aita,storytime,shorts')
    
    # Process tags
    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
    
    # Process title (max 100 chars)
    title = truncate_title(script_data.get('title', 'Untitled Story'))
    
    # Process description (ensure #shorts)
    description = ensure_shorts_tag(script_data.get('description', ''))
    
    # Build metadata structure
    metadata = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': category_id,
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': made_for_kids,
        }
    }
    
    return metadata


def print_metadata_preview(metadata: Dict):
    """Print a preview of the metadata that will be uploaded."""
    print("\n" + "=" * 60)
    print("METADATA PREVIEW")
    print("=" * 60)
    print(f"Title: {metadata['snippet']['title']}")
    print(f"\nDescription:\n{metadata['snippet']['description']}")
    print(f"\nTags: {', '.join(metadata['snippet']['tags'])}")
    print(f"Category ID: {metadata['snippet']['categoryId']}")
    print(f"Privacy: {metadata['status']['privacyStatus']}")
    print(f"Made for Kids: {metadata['status']['selfDeclaredMadeForKids']}")
    print("=" * 60 + "\n")
