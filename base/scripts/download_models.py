#!/usr/bin/env python3
"""
Enhanced Model Downloader for AiClipse ComfyUI
Supports HuggingFace Hub, Cloudflare R2, and CivitAI downloads
trigger
"""

import argparse
import os
import sys
import requests
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import urlparse
from huggingface_hub import hf_hub_download


def log(message):
    print(f"[MODELS] {message}", flush=True)


def log_error(message):
    print(f"[MODELS ERROR] {message}", flush=True, file=sys.stderr)


class EnhancedModelDownloader:
    def __init__(self, models_dir, hf_token=None, r2_config=None, civitai_token=None):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.hf_token = hf_token
        self.civitai_token = civitai_token

        # Initialize R2 client if configured
        self.r2_client = None
        self.r2_bucket = None
        if r2_config:
            self._init_r2_client(r2_config)

    def _init_r2_client(self, r2_config):
        """Initialize Cloudflare R2 client"""
        try:
            import boto3

            self.r2_client = boto3.client(
                "s3",
                endpoint_url=f"https://{r2_config['account_id']}.r2.cloudflarestorage.com",
                aws_access_key_id=r2_config["access_key"],
                aws_secret_access_key=r2_config["secret_key"],
                region_name="auto",
            )
            self.r2_bucket = r2_config.get("bucket")
            log("✅ R2 client initialized")
        except ImportError:
            log_error("boto3 not installed - install with: pip install boto3")
            log_error("R2 support disabled")
        except Exception as e:
            log_error(f"R2 client initialization failed: {e}")

    def parse_manifest_line(self, line, line_num):
        """Parse enhanced manifest line with backward compatibility"""
        parts = line.split("|")
        if len(parts) < 3:
            log_error(f"Line {line_num}: Invalid format - minimum 3 fields required")
            return None

        # Auto-detect format based on first field
        first_part = parts[0].strip().lower()

        # Enhanced format: source|identifier|filename|subdir[|checksum]
        if first_part in ["r2", "cloudflare", "civitai", "huggingface", "hf"]:
            if len(parts) < 4:
                log_error(
                    f"Line {line_num}: Enhanced format requires: source|identifier|filename|subdir[|checksum]"
                )
                return None

            return {
                "source": first_part,
                "identifier": parts[1].strip(),
                "filename": parts[2].strip(),
                "subdir": parts[3].strip(),
                "checksum": (
                    parts[4].strip() if len(parts) > 4 and parts[4].strip() else None
                ),
                "line_num": line_num,
            }

        # Legacy format: repo_id|filename|subdir[|checksum] (assumes HuggingFace)
        else:
            return {
                "source": "huggingface",
                "identifier": parts[0].strip(),
                "filename": parts[1].strip(),
                "subdir": parts[2].strip(),
                "checksum": (
                    parts[3].strip() if len(parts) > 3 and parts[3].strip() else None
                ),
                "line_num": line_num,
            }

    def download_huggingface(self, model_info):
        """Download from HuggingFace Hub"""
        try:
            repo_id = model_info["identifier"]
            filename = model_info["filename"]
            target_dir = self.models_dir / model_info["subdir"]
            target_dir.mkdir(parents=True, exist_ok=True)

            log(f"📥 Downloading from HuggingFace: {repo_id}/{filename}")

            downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=target_dir,
                token=self.hf_token,
                local_dir_use_symlinks=False,
            )

            return downloaded_path
        except Exception as e:
            raise Exception(f"HuggingFace download failed: {e}")

    def download_r2(self, model_info):
        """Download from Cloudflare R2"""
        if not self.r2_client:
            raise Exception(
                "R2 client not configured. Set R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ACCOUNT_ID environment variables"
            )

        try:
            # Handle identifier formats:
            # 1. "bucket/path/file.ext" - full path
            # 2. "path/file.ext" - use default bucket
            identifier = model_info["identifier"]

            if "/" in identifier and not self.r2_bucket:
                # Format: bucket/key
                bucket, key = identifier.split("/", 1)
            elif self.r2_bucket:
                # Use default bucket
                bucket = self.r2_bucket
                key = identifier
            else:
                raise Exception(
                    f"R2 identifier must include bucket or set R2_BUCKET environment variable. Got: {identifier}"
                )

            target_file = (
                self.models_dir / model_info["subdir"] / model_info["filename"]
            )
            target_file.parent.mkdir(parents=True, exist_ok=True)

            log(f"☁️ Downloading from R2: s3://{bucket}/{key}")

            # Check if object exists and get size
            try:
                response = self.r2_client.head_object(Bucket=bucket, Key=key)
                file_size = response.get("ContentLength", 0)
                log(f"📦 File size: {file_size:,} bytes")
            except Exception as e:
                raise Exception(f"Object not found in R2: s3://{bucket}/{key} - {e}")

            # Download file
            self.r2_client.download_file(bucket, key, str(target_file))

            return str(target_file)
        except Exception as e:
            raise Exception(f"R2 download failed: {e}")

    def download_civitai(self, model_info):
        """Download from CivitAI"""
        try:
            model_id = model_info["identifier"]
            requested_filename = model_info["filename"]

            # CivitAI API endpoint
            api_url = f"https://civitai.com/api/v1/models/{model_id}"

            headers = {
                "User-Agent": "AiClipse-ComfyUI/1.0 (https://github.com/nishit-g/aiclipse-comfyui)"
            }
            if self.civitai_token:
                headers["Authorization"] = f"Bearer {self.civitai_token}"

            log(f"🎨 Fetching CivitAI model info: {model_id}")

            # Get model info with retries
            for attempt in range(3):
                try:
                    response = requests.get(api_url, headers=headers, timeout=30)
                    response.raise_for_status()
                    model_data = response.json()
                    break
                except requests.RequestException as e:
                    if attempt == 2:
                        raise Exception(
                            f"Failed to fetch model info after 3 attempts: {e}"
                        )
                    log(f"⚠️ Attempt {attempt + 1} failed, retrying...")
                    time.sleep(2)

            # Find the right file
            download_url = None
            file_metadata = None
            actual_filename = requested_filename

            # Look through all versions and files
            for version in model_data.get("modelVersions", []):
                for file in version.get("files", []):
                    file_name = file.get("name", "")

                    # Match strategies:
                    # 1. Exact filename match
                    # 2. 'auto' or 'latest' - use primary file
                    # 3. Extension match (e.g., ".safetensors")
                    if (
                        file_name == requested_filename
                        or requested_filename.lower() in ["auto", "latest"]
                        and file.get("primary", False)
                        or requested_filename.startswith(".")
                        and file_name.endswith(requested_filename)
                    ):

                        download_url = file["downloadUrl"]
                        file_metadata = file
                        actual_filename = file_name
                        break

                if download_url:
                    break

            if not download_url:
                # Show available files for debugging
                available_files = []
                for version in model_data.get("modelVersions", [])[
                    :2
                ]:  # Show first 2 versions
                    version_name = version.get("name", "Unknown")
                    for file in version.get("files", []):
                        available_files.append(f"{file['name']} (v:{version_name})")

                raise Exception(
                    f"File '{requested_filename}' not found. Available files: {available_files[:10]}"
                )

            # Update filename if auto-detected
            model_info["filename"] = actual_filename

            # Prepare download
            target_file = self.models_dir / model_info["subdir"] / actual_filename
            target_file.parent.mkdir(parents=True, exist_ok=True)

            file_size = (
                file_metadata.get("sizeKB", 0) * 1024
                if file_metadata.get("sizeKB")
                else 0
            )
            log(f"🔥 Downloading from CivitAI: {actual_filename} ({file_size:,} bytes)")

            # Download with progress and retries
            for attempt in range(3):
                try:
                    with requests.get(
                        download_url, headers=headers, stream=True, timeout=60
                    ) as r:
                        r.raise_for_status()
                        total_size = int(r.headers.get("content-length", file_size))
                        downloaded = 0

                        with open(target_file, "wb") as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                                downloaded += len(chunk)

                                # Show progress every MB
                                if (
                                    downloaded % (1024 * 1024) == 0
                                    or downloaded == total_size
                                ):
                                    if total_size > 0:
                                        percent = (downloaded / total_size) * 100
                                        print(
                                            f"\r📥 Progress: {percent:.1f}% ({downloaded:,}/{total_size:,} bytes)",
                                            end="",
                                            flush=True,
                                        )

                        print()  # New line
                    break

                except requests.RequestException as e:
                    if attempt == 2:
                        raise Exception(f"Download failed after 3 attempts: {e}")
                    log(f"⚠️ Download attempt {attempt + 1} failed, retrying...")
                    if target_file.exists():
                        target_file.unlink()  # Remove partial file
                    time.sleep(5)

            return str(target_file)
        except Exception as e:
            raise Exception(f"CivitAI download failed: {e}")

    def verify_checksum(self, file_path, expected_checksum):
        """Verify file checksum (SHA256)"""
        if not expected_checksum:
            return True

        try:
            log(f"🔍 Verifying checksum for {Path(file_path).name}...")
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)

            actual_checksum = sha256_hash.hexdigest()
            matches = actual_checksum.lower() == expected_checksum.lower()

            if matches:
                log(f"✅ Checksum verified: {expected_checksum[:16]}...")
            else:
                log_error(
                    f"❌ Checksum mismatch! Expected: {expected_checksum[:16]}..., Got: {actual_checksum[:16]}..."
                )

            return matches
        except Exception as e:
            log_error(f"Checksum verification failed: {e}")
            return False

    def download_model(self, model_info):
        """Download model based on source type"""
        target_file = self.models_dir / model_info["subdir"] / model_info["filename"]

        # Check if file already exists and verify if needed
        if target_file.exists():
            if model_info["checksum"]:
                if self.verify_checksum(target_file, model_info["checksum"]):
                    log(
                        f"⭐ Skipping {model_info['filename']} (exists, checksum verified)"
                    )
                    return str(target_file)
                else:
                    log(f"🔄 Re-downloading {model_info['filename']} (checksum failed)")
                    target_file.unlink()
            else:
                log(f"⭐ Skipping {model_info['filename']} (already exists)")
                return str(target_file)

        # Download based on source type
        downloaders = {
            "huggingface": self.download_huggingface,
            "hf": self.download_huggingface,
            "r2": self.download_r2,
            "cloudflare": self.download_r2,
            "civitai": self.download_civitai,
        }

        downloader = downloaders.get(model_info["source"])
        if not downloader:
            raise Exception(
                f"Unsupported source type: {model_info['source']}. Supported: {list(downloaders.keys())}"
            )

        # Perform download
        downloaded_path = downloader(model_info)

        # Verify checksum if provided
        if model_info["checksum"]:
            if not self.verify_checksum(downloaded_path, model_info["checksum"]):
                log_error(
                    f"❌ Checksum verification failed for {model_info['filename']}"
                )
                if os.path.exists(downloaded_path):
                    os.remove(downloaded_path)
                return None

        # Success
        file_size = os.path.getsize(downloaded_path)
        log(f"✅ Downloaded: {model_info['filename']} ({file_size:,} bytes)")
        return downloaded_path

    def process_manifest(self, manifest_file):
        """Process manifest file with all source types"""
        if not os.path.exists(manifest_file):
            log_error(f"Manifest file not found: {manifest_file}")
            return False

        log(f"📋 Processing manifest: {manifest_file}")

        success_count = 0
        error_count = 0
        sources_used = set()

        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Count valid lines
            valid_lines = [
                l for l in lines if l.strip() and not l.strip().startswith("#")
            ]
            total_lines = len(valid_lines)

            if total_lines == 0:
                log("ℹ️ No models found in manifest")
                return True

            log(f"📦 Found {total_lines} models to download")

            for line_num, line in enumerate(lines, 1):
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                # Parse line
                model_info = self.parse_manifest_line(line, line_num)
                if not model_info:
                    error_count += 1
                    continue

                try:
                    sources_used.add(model_info["source"].upper())
                    downloaded_path = self.download_model(model_info)

                    if downloaded_path:
                        success_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    error_count += 1
                    log_error(f"Failed {model_info.get('filename', 'unknown')}: {e}")

                    # Clean up partial downloads
                    target_file = (
                        self.models_dir / model_info["subdir"] / model_info["filename"]
                    )
                    if target_file.exists() and target_file.stat().st_size == 0:
                        target_file.unlink()

        except Exception as e:
            log_error(f"Failed to process manifest: {e}")
            return False

        # Summary
        log(f"📊 Download summary: {success_count} success, {error_count} errors")
        if sources_used:
            log(f"🌐 Sources used: {', '.join(sorted(sources_used))}")

        if error_count > 0:
            log_error(
                f"⚠️ {error_count} downloads failed. Check logs above for details."
            )

        return error_count == 0


def load_config():
    """Load configuration from environment variables"""
    config = {
        "hf_token": os.getenv("HF_TOKEN"),
        "civitai_token": os.getenv("CIVITAI_TOKEN") or os.getenv("CIVITAI_API_KEY"),
        "r2_config": None,
    }

    # R2 configuration
    r2_access_key = os.getenv("R2_ACCESS_KEY_ID")
    r2_secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    r2_account_id = os.getenv("R2_ACCOUNT_ID")
    r2_bucket = os.getenv("R2_BUCKET")

    if all([r2_access_key, r2_secret_key, r2_account_id]):
        config["r2_config"] = {
            "access_key": r2_access_key,
            "secret_key": r2_secret_key,
            "account_id": r2_account_id,
            "bucket": r2_bucket,  # Optional default bucket
        }
        log("🔧 R2 configuration loaded")

    if config["civitai_token"]:
        log("🔧 CivitAI token loaded")

    if config["hf_token"]:
        log("🔧 HuggingFace token loaded")

    return config


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced model downloader supporting HuggingFace, Cloudflare R2, and CivitAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download from manifest
  python download_models.py --manifest models.txt --models-dir /workspace/models

  # Validate manifest only
  python download_models.py --manifest models.txt --models-dir /tmp --validate-only

Manifest format:
  # Legacy HuggingFace format
  repo_id|filename|subdir[|checksum]

  # Enhanced format with source
  huggingface|repo_id|filename|subdir[|checksum]
  r2|bucket/path/file.ext|filename|subdir[|checksum]
  civitai|model_id|filename|subdir[|checksum]

Environment variables:
  HF_TOKEN - HuggingFace Hub token
  CIVITAI_TOKEN - CivitAI API token
  R2_ACCESS_KEY_ID - Cloudflare R2 access key
  R2_SECRET_ACCESS_KEY - Cloudflare R2 secret key
  R2_ACCOUNT_ID - Cloudflare R2 account ID
  R2_BUCKET - Default R2 bucket (optional)
        """,
    )

    parser.add_argument("--manifest", required=True, help="Path to manifest file")
    parser.add_argument("--models-dir", required=True, help="Models download directory")
    parser.add_argument(
        "--validate-only", action="store_true", help="Only validate manifest syntax"
    )

    args = parser.parse_args()

    if not os.path.exists(args.manifest):
        log_error(f"Manifest file not found: {args.manifest}")
        return 1

    # Load configuration from environment
    config = load_config()

    # Initialize downloader
    try:
        downloader = EnhancedModelDownloader(args.models_dir, **config)
    except Exception as e:
        log_error(f"Failed to initialize downloader: {e}")
        return 1

    # Validate only mode
    if args.validate_only:
        log("🔍 Validating manifest syntax...")

        with open(args.manifest, "r", encoding="utf-8") as f:
            valid = True
            line_count = 0

            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                line_count += 1
                if not downloader.parse_manifest_line(line, line_num):
                    valid = False

        if valid:
            log(f"✅ Manifest validation passed ({line_count} valid entries)")
            return 0
        else:
            log_error("❌ Manifest validation failed")
            return 1

    # Process manifest
    try:
        success = downloader.process_manifest(args.manifest)
        return 0 if success else 1
    except KeyboardInterrupt:
        log_error("\n🛑 Download interrupted by user")
        return 130
    except Exception as e:
        log_error(f"Download process failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
