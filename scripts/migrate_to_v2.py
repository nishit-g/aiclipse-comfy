"""
Modal Volume v2 Migration Script
Copies all models from aiclipse-models (v1) to aiclipse-models-v2

Run with: modal run scripts/migrate_to_v2.py
"""

import modal
import subprocess
import sys

app = modal.App("volume-migration")

# Mount both volumes
v1_models = modal.Volume.from_name("aiclipse-models")
v2_models = modal.Volume.from_name("aiclipse-models-v2")
v1_outputs = modal.Volume.from_name("aiclipse-outputs")
v2_outputs = modal.Volume.from_name("aiclipse-outputs-v2")


@app.function(
    volumes={
        "/v1/models": v1_models,
        "/v2/models": v2_models,
        "/v1/outputs": v1_outputs,
        "/v2/outputs": v2_outputs,
    },
    timeout=60 * 60 * 4,  # 4 hours max
    memory=4096,  # 4GB RAM for rsync
    cpu=4.0,
)
def migrate_volumes():
    """Copy all files from v1 volumes to v2 volumes using rsync"""
    import os
    
    print("=" * 60)
    print("Modal Volume v2 Migration")
    print("=" * 60)
    
    # Check v1 models content
    print("\n📂 V1 Models Volume Contents:")
    subprocess.run(["ls", "-la", "/v1/models"], check=False)
    
    print("\n📂 V1 Outputs Volume Contents:")
    subprocess.run(["ls", "-la", "/v1/outputs"], check=False)
    
    # Install rsync if not available
    print("\n📦 Installing rsync...")
    subprocess.run(["apt-get", "update", "-qq"], check=False)
    subprocess.run(["apt-get", "install", "-y", "-qq", "rsync"], check=False)
    
    # Migrate models
    print("\n" + "=" * 60)
    print("🚀 Migrating Models (v1 -> v2)")
    print("This may take a while for large models (~40GB)...")
    print("=" * 60)
    
    result = subprocess.run(
        [
            "rsync", "-av", "--progress",
            "--exclude", ".cache",  # Skip cache directories
            "/v1/models/",
            "/v2/models/"
        ],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    if result.returncode != 0:
        print(f"⚠️ rsync for models returned code {result.returncode}")
    
    # Sync to persist changes
    print("\n💾 Syncing v2 models volume...")
    subprocess.run(["sync", "/v2/models"], check=False)
    v2_models.commit()
    
    # Migrate outputs
    print("\n" + "=" * 60)
    print("🚀 Migrating Outputs (v1 -> v2)")
    print("=" * 60)
    
    result = subprocess.run(
        [
            "rsync", "-av", "--progress",
            "/v1/outputs/",
            "/v2/outputs/"
        ],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    if result.returncode != 0:
        print(f"⚠️ rsync for outputs returned code {result.returncode}")
    
    # Sync to persist changes
    print("\n💾 Syncing v2 outputs volume...")
    subprocess.run(["sync", "/v2/outputs"], check=False)
    v2_outputs.commit()
    
    # Verify migration
    print("\n" + "=" * 60)
    print("✅ Verification - V2 Volumes Content:")
    print("=" * 60)
    
    print("\n📂 V2 Models Volume:")
    subprocess.run(["ls", "-la", "/v2/models"], check=False)
    
    # Check file sizes
    print("\n📊 Models Size Comparison:")
    print("V1:")
    subprocess.run(["du", "-sh", "/v1/models"], check=False)
    print("V2:")
    subprocess.run(["du", "-sh", "/v2/models"], check=False)
    
    print("\n📂 V2 Outputs Volume:")
    subprocess.run(["ls", "-la", "/v2/outputs"], check=False)
    
    print("\n" + "=" * 60)
    print("🎉 Migration Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Update app.py to use 'aiclipse-models-v2' and 'aiclipse-outputs-v2'")
    print("2. Redeploy the app")
    print("3. Once verified, delete old v1 volumes:")
    print("   modal volume delete aiclipse-models")
    print("   modal volume delete aiclipse-outputs")


@app.local_entrypoint()
def main():
    migrate_volumes.remote()
