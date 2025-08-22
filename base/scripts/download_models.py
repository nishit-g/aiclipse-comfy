#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path
from huggingface_hub import hf_hub_download, snapshot_download


def log(message):
    print(f"[MODELS] {message}", flush=True)


def download_from_manifest(manifest_file, models_dir, token=None):
    """Download models from manifest file"""
    models_dir = Path(models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    error_count = 0

    with open(manifest_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            try:
                # Parse manifest line: repo|filename|subdir
                parts = line.split("|", 2)
                if len(parts) != 3:
                    log(f"Line {line_num}: Invalid format, skipping: {line}")
                    continue

                repo_id, filename, subdir = parts

                # Create target directory
                target_dir = models_dir / subdir
                target_dir.mkdir(parents=True, exist_ok=True)

                # Download file
                log(f"Downloading {repo_id}/{filename} -> {subdir}/")
                downloaded_path = hf_hub_download(
                    repo_id=repo_id,
                    filename=filename,
                    local_dir=target_dir,
                    token=token,
                )

                success_count += 1
                log(f"✅ Downloaded: {downloaded_path}")

            except Exception as e:
                error_count += 1
                log(f"❌ Failed {repo_id}/{filename}: {e}")

    log(f"Download complete: {success_count} success, {error_count} errors")
    return error_count == 0


def main():
    parser = argparse.ArgumentParser(description="Download models from manifest")
    parser.add_argument("--manifest", required=True, help="Manifest file path")
    parser.add_argument("--models-dir", required=True, help="Models directory")
    parser.add_argument(
        "--token", default=os.getenv("HF_TOKEN"), help="Hugging Face token"
    )

    args = parser.parse_args()

    if not os.path.exists(args.manifest):
        log(f"Manifest file not found: {args.manifest}")
        return 1

    try:
        success = download_from_manifest(args.manifest, args.models_dir, args.token)
        return 0 if success else 1
    except Exception as e:
        log(f"Download failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
