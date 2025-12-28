"""
Modal Secrets Configuration
===========================
Handles environment variables and sensitive credentials.

Setup:
    modal secret create aiclipse-env \
        HF_TOKEN=hf_xxx \
        CIVITAI_TOKEN=xxx \
        R2_ACCESS_KEY_ID=xxx \
        R2_SECRET_ACCESS_KEY=xxx \
        R2_ACCOUNT_ID=xxx \
        R2_BUCKET=aiclipse-models
"""
import modal
from typing import Optional

# =============================================================================
# Secret Definitions
# =============================================================================

# Main environment secret (all credentials)
AICLIPSE_SECRET_NAME = "aiclipse-env"

def get_secrets() -> list:
    """
    Return list of Modal secrets for function decorators.
    Creates secret if it doesn't exist (returns empty list).
    """
    try:
        return [modal.Secret.from_name(AICLIPSE_SECRET_NAME)]
    except modal.exception.NotFoundError:
        # Secret doesn't exist yet - user needs to create it
        print(f"[WARN] Secret '{AICLIPSE_SECRET_NAME}' not found. Create it with:")
        print(f"  modal secret create {AICLIPSE_SECRET_NAME} HF_TOKEN=xxx ...")
        return []

# =============================================================================
# Required Environment Variables
# =============================================================================

REQUIRED_SECRETS = {
    "HF_TOKEN": "HuggingFace access token for gated models",
}

OPTIONAL_SECRETS = {
    "CIVITAI_TOKEN": "CivitAI API token for model downloads",
    "R2_ACCESS_KEY_ID": "Cloudflare R2 access key",
    "R2_SECRET_ACCESS_KEY": "Cloudflare R2 secret key",
    "R2_ACCOUNT_ID": "Cloudflare R2 account ID",
    "R2_BUCKET": "R2 bucket name for models",
    "PUBLIC_KEY": "SSH public key for container access",
}

def validate_secrets() -> dict:
    """Check which secrets are configured (call from within function)."""
    import os
    status = {}
    for key in {**REQUIRED_SECRETS, **OPTIONAL_SECRETS}:
        status[key] = bool(os.environ.get(key))
    return status
