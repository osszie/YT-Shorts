#!/usr/bin/env python3
"""OAuth authentication for YouTube Data API v3."""

import os
import pathlib
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_youtube_client(project_root: pathlib.Path):
    credentials_file = project_root / os.getenv("YOUTUBE_CLIENT_SECRETS", "credentials.json")
    token_file = project_root / os.getenv("YOUTUBE_TOKEN_FILE", "token.json")

    creds = None
    if token_file.exists():
        try:
            import json
            try:
                with open(token_file, "r") as token:
                    creds = Credentials.from_authorized_user_info(json.load(token), SCOPES)
            except (json.JSONDecodeError, ValueError, KeyError):
                with open(token_file, "rb") as token:
                    creds = pickle.load(token)
        except Exception as e:
            print(f"⚠️  Could not load token: {e}; requesting new authorization...")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_file.exists():
                raise FileNotFoundError(
                    f"Credentials file not found: {credentials_file}\n"
                    "Download credentials.json (OAuth Desktop app) from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
            creds = flow.run_local_server(port=0)
        try:
            import json
            with open(token_file, "w") as token:
                json.dump({
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": creds.scopes,
                }, token)
        except Exception:
            with open(token_file, "wb") as token:
                pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)
