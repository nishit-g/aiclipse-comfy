#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path
from huggingface_hub import hf_hub_download, snapshot_download


def log(message):
    print(f"[MODELS] {message}", flush=True)


def log_error(message):
    print(f"[MODELS ERROR] {message}", flush=True, file=sys.stderr)


def validate_manifest_line(line, line_num):
    """Validate and parse a manifest line"""
    parts = line.split("|", 2)
    if len(parts) != 3:
        log_error(
            f"Line {line_num}: Invalid format '{line}' - Expected: repo_id|filename|subdir"
        )
        return None

    repo_id, filename, subdir = [p.strip() for p in parts]

    # Validate all fields are non-empty
    if not all([repo_id, filename, subdir]):
        log_error(
            f"Line {line_num}: Empty fields not allowed - repo_id='{repo_id}' filename='{filename}' subdir='{subdir}'"
        )
        return None

    # Basic validation
    if not repo_id.count("/") >= 1:
        log_error(
            f"Line {line_num}: Invalid repo_id format '{repo_id}' - Expected: owner/repo"
        )
        return None

    if "/" in filename and not filename.startswith("./"):
        log_error(
            f"Line {line_num}: Suspicious filename '{filename}' - paths not allowed"
        )
        return None

    return repo_id, filename, subdir


def download_from_manifest(manifest_file, models_dir, token=None):
    """Download models from manifest file"""
    models_dir = Path(models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    error_count = 0

    if not os.path.exists(manifest_file):
        log_error(f"Manifest file not found: {manifest_file}")
        return False

    log(f"📋 Reading manifest: {manifest_file}")
    log(f"📁 Target directory: {models_dir}")

    try:
        with open(manifest_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        total_lines = len(
            [l for l in lines if l.strip() and not l.strip().startswith("#")]
        )
        log(f"📦 Found {total_lines} models to download")

        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Validate and parse line
            parsed = validate_manifest_line(line, line_num)
            if not parsed:
                error_count += 1
                continue

            repo_id, filename, subdir = parsed

            try:
                # Create target directory
                target_dir = models_dir / subdir
                target_dir.mkdir(parents=True, exist_ok=True)

                # Check if file already exists
                target_file = target_dir / filename
                if target_file.exists():
                    log(f"⏭️  Skipping {repo_id}/{filename} (already exists)")
                    success_count += 1
                    continue

                # Download file
                log(f"📥 Downloading {repo_id}/{filename} -> {subdir}/")

                downloaded_path = hf_hub_download(
                    repo_id=repo_id,
                    filename=filename,
                    local_dir=target_dir,
                    token=token,
                    local_dir_use_symlinks=False,  # Avoid symlinks for compatibility
                )

                # Verify download
                if os.path.exists(downloaded_path):
                    file_size = os.path.getsize(downloaded_path)
                    log(f"✅ Downloaded: {downloaded_path} ({file_size:,} bytes)")
                    success_count += 1
                else:
                    log_error(
                        f"Download completed but file not found: {downloaded_path}"
                    )
                    error_count += 1

            except Exception as e:
                error_count += 1
                log_error(f"Failed {repo_id}/{filename}: {e}")

                # Clean up partial downloads
                target_file = target_dir / filename
                if target_file.exists() and target_file.stat().st_size == 0:
                    target_file.unlink()
                    log(f"🧹 Cleaned up empty file: {target_file}")

    except Exception as e:
        log_error(f"Failed to process manifest: {e}")
        return False

    log(f"📊 Download complete: {success_count} success, {error_count} errors")

    if error_count > 0:
        log_error(f"⚠️  {error_count} downloads failed. Check logs above for details.")

    return error_count == 0


def main():
    parser = argparse.ArgumentParser(description="Download models from manifest")
    parser.add_argument("--manifest", required=True, help="Manifest file path")
    parser.add_argument("--models-dir", required=True, help="Models directory")
    parser.add_argument(
        "--token", default=os.getenv("HF_TOKEN"), help="Hugging Face token"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate manifest, don't download",
    )

    args = parser.parse_args()

    if not os.path.exists(args.manifest):
        log_error(f"Manifest file not found: {args.manifest}")
        return 1

    # Validate manifest first
    if args.validate_only:
        log("🔍 Validating manifest only...")
        with open(args.manifest, "r", encoding="utf-8") as f:
            valid = True
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if not validate_manifest_line(line, line_num):
                    valid = False
        return 0 if valid else 1

    try:
        success = download_from_manifest(args.manifest, args.models_dir, args.token)
        return 0 if success else 1
    except Exception as e:
        log_error(f"Download failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
