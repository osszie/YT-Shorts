# YouTube Upload Agent - Phase 4

Modular YouTube upload system with dry-run support.

## Environment Variables

Add these to your `.env` file:

```bash
# YouTube Upload settings (Phase 4)
YOUTUBE_CLIENT_SECRETS=credentials.json
YOUTUBE_TOKEN_FILE=token.json
YOUTUBE_PRIVACY_STATUS=private  # Options: private, unlisted, public
YOUTUBE_CATEGORY_ID=24  # Entertainment (see YouTube category IDs)
YOUTUBE_MADE_FOR_KIDS=false
YOUTUBE_TAGS=aita,storytime,shorts
YOUTUBE_DRY_RUN=true  # Set to false to enable actual uploads
```

## Usage

```bash
python scripts/upload_youtube.py
```

## Modules

- `validate.py` - Validates prerequisites (files, metadata, video properties)
- `metadata.py` - Builds YouTube metadata from script.json
- `auth.py` - Handles OAuth authentication
- `upload.py` - Performs upload (with dry-run support)
