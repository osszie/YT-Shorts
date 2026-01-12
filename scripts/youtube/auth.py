#!/usr/bin/env python3
"""
OAuth authentication for YouTube Data API v3.
Handles token management and client creation.
"""

import os
import pathlib
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


# YouTube API scope for uploading videos
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


def get_youtube_client(project_root: pathlib.Path):
    """
    Authenticate and return YouTube API client.
    
    Args:
        project_root: Path to project root directory
        
    Returns:
        YouTube API service client
        
    Raises:
        FileNotFoundError: If credentials.json is missing
        Exception: For authentication errors
    """
    credentials_file = project_root / os.getenv('YOUTUBE_CLIENT_SECRETS', 'credentials.json')
    token_file = project_root / os.getenv('YOUTUBE_TOKEN_FILE', 'token.json')
    
    creds = None
    
    # Load existing token if available
    if token_file.exists():
        try:
            import json
            # Try JSON format first (preferred)
            try:
                with open(token_file, 'r') as token:
                    token_data = json.load(token)
                    creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            except (json.JSONDecodeError, ValueError, KeyError):
                # Fall back to pickle format (for compatibility)
                with open(token_file, 'rb') as token:
                    creds = pickle.load(token)
        except Exception as e:
            print(f"⚠️  Could not load existing token: {e}")
            print("   Will request new authorization...")
    
    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            creds.refresh(Request())
        else:
            if not credentials_file.exists():
                raise FileNotFoundError(
                    f"Credentials file not found: {credentials_file}\n"
                    "Please download credentials.json from Google Cloud Console."
                )
            
            print("🔐 Starting OAuth flow...")
            print("   A browser window will open for authorization.")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_file), SCOPES)
            creds = flow.run_local_server(port=0)
            print("✅ Authorization successful!")
        
        # Save credentials for next run
        print(f"💾 Saving token to {token_file}...")
        try:
            # Try JSON format (more portable)
            token_data = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes
            }
            import json
            with open(token_file, 'w') as token:
                json.dump(token_data, token)
        except Exception:
            # Fall back to pickle
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
    
    # Build and return YouTube API client
    return build('youtube', 'v3', credentials=creds)
