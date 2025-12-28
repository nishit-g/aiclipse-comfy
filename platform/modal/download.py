"""
CPU-Based Model Downloader
==========================
Downloads models to Modal Volume using CPU (cheap!).
Reads templates/*/config.yaml - SAME format as RunPod.

Run BEFORE deploying GPU server for instant cold starts.

Usage:
    modal run platform/modal/download.py --template boomboom
"""
import modal
import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# =============================================================================
# Configuration
# =============================================================================

MODELS_VOLUME_PATH = "/modal-volumes/models"
SECRET_NAME = "aiclipse-env"

# =============================================================================
# Config Loader (same as serve.py)
# =============================================================================

@dataclass
class ModelConfig:
    source: str
    repo: str = ""
    file: str = ""
    path: str = ""
    key: str = ""


@dataclass
class TemplateConfig:
    name: str
    models: list = field(default_factory=list)


def load_template_models(template: str, templates_dir: Path) -> list[ModelConfig]:
    """Load models from template config.yaml."""
    config_path = templates_dir / template / "config.yaml"
    
    if not config_path.exists():
        print(f"[DOWNLOAD] Config not found: {config_path}")
        return []
    
    with open(config_path) as f:
        data = yaml.safe_load(f)
    
    models = []
    for m in data.get("models", []):
        models.append(ModelConfig(
            source=m.get("source", "huggingface"),
            repo=m.get("repo", ""),
            file=m.get("file", ""),
            path=m.get("path", ""),
            key=m.get("key", ""),
        ))
    
    return models


# =============================================================================
# Modal App
# =============================================================================

app = modal.App("aiclipse-download")

models_volume = modal.Volume.from_name("aiclipse-models", create_if_missing=True)

# Lightweight CPU image for downloads
download_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("aria2", "git", "curl")
    .pip_install(
        "huggingface-hub[hf_xet]",
        "boto3",
        "requests",
        "pyyaml",
        "tqdm",
    )
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "HF_XET_HIGH_PERFORMANCE": "1",
    })
    # Add templates directory for config access
    .add_local_dir(
        str(Path(__file__).parent.parent.parent / "templates"),
        remote_path="/templates",
        copy=True,
    )
)


# =============================================================================
# Download Function
# =============================================================================

@app.function(
    image=download_image,
    volumes={MODELS_VOLUME_PATH: models_volume},
    cpu=4,
    memory=8192,
    timeout=7200,  # 2 hours
)
def download_models_for_template(template: str = "boomboom"):
    """
    Download all models for a template to Modal Volume.
    
    Reads models from templates/{template}/config.yaml
    Downloads to Volume using HuggingFace Hub or R2/boto3.
    """
    from huggingface_hub import hf_hub_download
    
    print("=" * 60)
    print(f"[DOWNLOAD] AiClipse Model Downloader")
    print(f"[DOWNLOAD] Template: {template}")
    print("=" * 60)
    
    # Get HF token if available
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        print("[DOWNLOAD] ✅ HF_TOKEN configured")
    else:
        print("[DOWNLOAD] ⚠️ No HF_TOKEN - some gated models may fail")
    
    # Load models from config.yaml
    models = load_template_models(template, Path("/templates"))
    
    if not models:
        print("[DOWNLOAD] ❌ No models found in config")
        return {"files": 0, "size_gb": 0}
    
    print(f"[DOWNLOAD] Found {len(models)} models in config.yaml")
    
    # Create model directories
    models_dir = Path(MODELS_VOLUME_PATH)
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Download each model
    downloaded = 0
    skipped = 0
    failed = 0
    
    for model in models:
        target_dir = models_dir / model.path
        target_dir.mkdir(parents=True, exist_ok=True)
        
        if model.source in ("huggingface", "hf"):
            # Handle split_files path (file contains subdirectory)
            if "/" in model.file:
                # File like "split_files/diffusion_models/model.safetensors"
                actual_file = model.file.split("/")[-1]
                target_file = target_dir / actual_file
            else:
                target_file = target_dir / model.file
            
            if target_file.exists():
                print(f"[DOWNLOAD] ⏭️ Exists: {model.file}")
                skipped += 1
                continue
            
            print(f"[DOWNLOAD] ⬇️ {model.repo}/{model.file}")
            
            try:
                hf_hub_download(
                    repo_id=model.repo,
                    filename=model.file,
                    local_dir=str(target_dir),
                    local_dir_use_symlinks=False,
                    token=hf_token,
                )
                print(f"[DOWNLOAD] ✅ Downloaded: {model.file}")
                downloaded += 1
            except Exception as e:
                print(f"[DOWNLOAD] ❌ Failed: {model.file} - {e}")
                failed += 1
        
        elif model.source == "r2":
            # R2 download
            target_file = target_dir / (model.file or model.key.split("/")[-1])
            
            if target_file.exists():
                print(f"[DOWNLOAD] ⏭️ Exists: {model.key}")
                skipped += 1
                continue
            
            r2_key = os.environ.get("R2_ACCESS_KEY_ID")
            r2_secret = os.environ.get("R2_SECRET_ACCESS_KEY")
            r2_account = os.environ.get("R2_ACCOUNT_ID")
            r2_bucket = os.environ.get("R2_BUCKET")
            
            if not all([r2_key, r2_secret, r2_bucket]):
                print(f"[DOWNLOAD] ⚠️ R2 not configured, skipping: {model.key}")
                skipped += 1
                continue
            
            print(f"[DOWNLOAD] ⬇️ R2: {model.key}")
            
            try:
                import boto3
                s3 = boto3.client(
                    "s3",
                    endpoint_url=f"https://{r2_account}.r2.cloudflarestorage.com",
                    aws_access_key_id=r2_key,
                    aws_secret_access_key=r2_secret,
                )
                s3.download_file(r2_bucket, model.key, str(target_file))
                print(f"[DOWNLOAD] ✅ Downloaded from R2: {model.key}")
                downloaded += 1
            except Exception as e:
                print(f"[DOWNLOAD] ❌ R2 Failed: {model.key} - {e}")
                failed += 1
    
    # Commit to Volume
    print()
    print("[DOWNLOAD] Committing to Volume...")
    models_volume.commit()
    
    # Summary
    total_size = sum(f.stat().st_size for f in models_dir.rglob("*") if f.is_file())
    total_files = len(list(models_dir.rglob("*.safetensors")))
    
    print()
    print("=" * 60)
    print("[DOWNLOAD] Complete!")
    print(f"  Downloaded: {downloaded}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed: {failed}")
    print(f"  Total files: {total_files}")
    print(f"  Total size: {total_size / 1e9:.2f} GB")
    print("=" * 60)
    
    return {
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
        "total_files": total_files,
        "size_gb": total_size / 1e9,
    }


# =============================================================================
# List Models Function
# =============================================================================

@app.function(
    image=download_image,
    volumes={MODELS_VOLUME_PATH: models_volume},
)
def list_volume_models():
    """List models currently in the Volume."""
    models_dir = Path(MODELS_VOLUME_PATH)
    
    print("=" * 60)
    print("[VOLUME] Models in aiclipse-models Volume")
    print("=" * 60)
    
    if not models_dir.exists():
        print("  (empty)")
        return []
    
    files = list(models_dir.rglob("*.safetensors"))
    
    for subdir in sorted(set(f.parent.name for f in files)):
        subdir_files = [f for f in files if f.parent.name == subdir]
        print(f"\n📁 {subdir}/")
        for f in subdir_files:
            size_mb = f.stat().st_size / 1e6
            print(f"   - {f.name} ({size_mb:.1f} MB)")
    
    total_size = sum(f.stat().st_size for f in files)
    print(f"\n📊 Total: {len(files)} files, {total_size / 1e9:.2f} GB")
    
    return [str(f.relative_to(models_dir)) for f in files]


# =============================================================================
# CLI Entrypoint
# =============================================================================

@app.local_entrypoint()
def main(template: str = "boomboom", list_only: bool = False):
    """
    Download models for a template.
    
    Args:
        template: Template name (boomboom, sd15-basic, etc.)
        list_only: Just list current Volume contents
    """
    if list_only:
        list_volume_models.remote()
        return
    
    print(f"Downloading models for template: {template}")
    print("This runs on CPU (cheap!) and downloads to a Modal Volume.")
    print()
    
    result = download_models_for_template.remote(template)
    
    print()
    print(f"✅ Download complete!")
    print(f"   Files: {result['total_files']}")
    print(f"   Size: {result['size_gb']:.2f} GB")
    print()
    print("Now deploy with: modal deploy platform/modal/serve.py")
