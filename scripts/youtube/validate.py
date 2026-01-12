#!/usr/bin/env python3
"""
Validation module for YouTube upload prerequisites.
Validates files, metadata, and video properties.
"""

import os
import json
import pathlib
import subprocess
from typing import Dict, List, Tuple


def validate_script_json(script_path: pathlib.Path) -> Tuple[bool, List[str]]:
    """
    Validate script.json structure and required fields.
    
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    
    if not script_path.exists():
        errors.append(f"❌ Missing: {script_path}")
        errors.append("   → Run Phase 1 (scripts/agent.py) to generate script.json")
        return False, errors
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"❌ Invalid JSON in {script_path}: {e}")
        return False, errors
    
    # Check required fields
    required_fields = ['title', 'description', 'script']
    for field in required_fields:
        if field not in data:
            errors.append(f"❌ Missing field in script.json: '{field}'")
        elif not isinstance(data[field], str):
            errors.append(f"❌ Field '{field}' must be a string")
        elif not data[field].strip():
            errors.append(f"❌ Field '{field}' is empty")
    
    if errors:
        return False, errors
    
    return True, []


def validate_video_file(video_path: pathlib.Path) -> Tuple[bool, List[str]]:
    """
    Validate final.mp4 using ffprobe.
    Checks duration > 3 seconds and file size > 1MB.
    
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    
    if not video_path.exists():
        errors.append(f"❌ Missing: {video_path}")
        errors.append("   → Run Phase 3 (scripts/render.py) to generate final.mp4")
        return False, errors
    
    # Check file size
    file_size = video_path.stat().st_size
    min_size = 1024 * 1024  # 1MB
    if file_size < min_size:
        errors.append(f"❌ Video file too small: {file_size / 1024:.1f}KB (minimum 1MB)")
    
    # Check duration using ffprobe
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            errors.append(f"❌ ffprobe failed: {result.stderr}")
        else:
            try:
                duration = float(result.stdout.strip())
                min_duration = 3.0
                if duration < min_duration:
                    errors.append(f"❌ Video too short: {duration:.1f}s (minimum 3s)")
            except ValueError:
                errors.append(f"❌ Could not parse video duration from ffprobe output")
    except FileNotFoundError:
        errors.append("❌ ffprobe not found. Install FFmpeg: brew install ffmpeg")
    except subprocess.TimeoutExpired:
        errors.append("❌ ffprobe timed out while analyzing video")
    except Exception as e:
        errors.append(f"❌ Error checking video: {e}")
    
    if errors:
        return False, errors
    
    return True, []


def validate_credentials(credentials_path: pathlib.Path) -> Tuple[bool, List[str]]:
    """
    Validate credentials.json exists and is readable.
    
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    
    if not credentials_path.exists():
        errors.append(f"❌ Missing: {credentials_path}")
        errors.append("   → Download from Google Cloud Console:")
        errors.append("     1. Go to https://console.cloud.google.com/")
        errors.append("     2. Create/select project")
        errors.append("     3. Enable YouTube Data API v3")
        errors.append("     4. Create OAuth 2.0 credentials (Desktop app)")
        errors.append("     5. Download and save as 'credentials.json' in project root")
        return False, errors
    
    # Try to parse as JSON
    try:
        with open(credentials_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check for expected OAuth structure
        if 'installed' not in data and 'web' not in data:
            errors.append("❌ credentials.json doesn't appear to be OAuth credentials")
            errors.append("   → Ensure you downloaded OAuth 2.0 Desktop app credentials")
    except json.JSONDecodeError:
        errors.append("❌ credentials.json is not valid JSON")
    except Exception as e:
        errors.append(f"❌ Error reading credentials.json: {e}")
    
    if errors:
        return False, errors
    
    return True, []


def validate_all(project_root: pathlib.Path) -> Tuple[bool, Dict[str, List[str]]]:
    """
    Run all validation checks and return results.
    
    Returns:
        (all_valid, dict_of_results)
    """
    results = {
        'script_json': [],
        'video_file': [],
        'credentials': []
    }
    
    script_path = project_root / 'output' / 'script.json'
    video_path = project_root / 'output' / 'final.mp4'
    credentials_path = project_root / 'credentials.json'
    
    # Validate script.json
    is_valid, errors = validate_script_json(script_path)
    results['script_json'] = errors
    script_valid = is_valid
    
    # Validate video file
    is_valid, errors = validate_video_file(video_path)
    results['video_file'] = errors
    video_valid = is_valid
    
    # Validate credentials
    is_valid, errors = validate_credentials(credentials_path)
    results['credentials'] = errors
    credentials_valid = is_valid
    
    all_valid = script_valid and video_valid and credentials_valid
    
    return all_valid, results


def print_validation_report(results: Dict[str, List[str]]):
    """Print a formatted validation report."""
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)
    
    checks = [
        ('script_json', 'Script JSON (output/script.json)'),
        ('video_file', 'Video File (output/final.mp4)'),
        ('credentials', 'OAuth Credentials (credentials.json)')
    ]
    
    all_passed = True
    for key, label in checks:
        errors = results.get(key, [])
        if errors:
            all_passed = False
            print(f"\n{label}:")
            for error in errors:
                print(f"  {error}")
        else:
            print(f"\n✅ {label}: OK")
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("✅ ALL CHECKS PASSED")
    else:
        print("❌ VALIDATION FAILED - Fix errors above before proceeding")
    
    print("=" * 60 + "\n")
    
    return all_passed
