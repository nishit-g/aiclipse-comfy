"""
AiClipse ComfyUI - RunPod Entrypoint
Enterprise entrypoint with:
- SSH daemon setup
- Custom node installation
- Model path configuration
- Environment variable overrides
- JupyterLab (optional)
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Add library to path
sys.path.insert(0, "/app")

from aiclipse import Config, ModelDownloader, setup_model_paths, ComfyLauncher, install_custom_nodes
from aiclipse.gpu import get_gpu_config

# =============================================================================
# Configuration
# =============================================================================
TEMPLATE_NAME = os.environ.get("TEMPLATE_NAME", "qwen-multi-edit")
GPU_VARIANT = os.environ.get("GPU_VARIANT", "rtx4090")
CONFIG_PATH = Path("/app/config.yaml")
MODELS_PATH = Path(os.environ.get("MODELS_PATH", "/runpod-volume/models"))
OUTPUTS_PATH = Path(os.environ.get("OUTPUTS_PATH", "/runpod-volume/outputs"))
COMFY_PATH = Path(os.environ.get("COMFY_PATH", "/root/comfy"))

# Optional features
ENABLE_SSH = os.environ.get("ENABLE_SSH", "true").lower() == "true"
ENABLE_JUPYTER = os.environ.get("ENABLE_JUPYTER", "false").lower() == "true"
PUBLIC_KEY = os.environ.get("PUBLIC_KEY")
SSH_PASSWORD = os.environ.get("SSH_PASSWORD")


def setup_ssh():
    """Setup SSH daemon with key or password auth."""
    if not ENABLE_SSH:
        print("⏭️  SSH disabled")
        return
    
    print("\n🔐 Setting up SSH...")
    
    # Ensure directory exists
    ssh_dir = Path.home() / ".ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate host keys if missing
    for key_type in ["rsa", "ecdsa", "ed25519"]:
        key_file = Path(f"/etc/ssh/ssh_host_{key_type}_key")
        if not key_file.exists():
            subprocess.run([
                "ssh-keygen", "-t", key_type, "-f", str(key_file), "-q", "-N", ""
            ], check=True)
    
    # Setup authentication
    if PUBLIC_KEY:
        auth_file = ssh_dir / "authorized_keys"
        with open(auth_file, "a") as f:
            f.write(f"{PUBLIC_KEY}\n")
        auth_file.chmod(0o600)
        print("   ✅ Public key authentication configured")
    else:
        # Generate or use provided password
        import secrets
        password = SSH_PASSWORD or secrets.token_urlsafe(12)
        subprocess.run(["chpasswd"], input=f"root:{password}".encode(), check=True)
        
        # Save password to file
        pass_file = OUTPUTS_PATH / ".ssh_password"
        with open(pass_file, "w") as f:
            f.write(password)
        pass_file.chmod(0o600)
        print(f"   ✅ Password saved to {pass_file}")
    
    # Start SSH daemon
    subprocess.run(["/usr/sbin/sshd"], check=True)
    print("   ✅ SSH daemon started")


def setup_jupyter():
    """Start JupyterLab if enabled."""
    if not ENABLE_JUPYTER:
        return
    
    print("\n📓 Starting JupyterLab...")
    
    token = os.environ.get("JUPYTER_TOKEN", "")
    logs_dir = OUTPUTS_PATH / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "jupyter", "lab",
        "--ip=0.0.0.0",
        "--port=8888",
        "--no-browser",
        f"--ServerApp.token={token}",
        "--ServerApp.allow_origin=*",
        "--ServerApp.root_dir=/workspace",
        "--ServerApp.allow_root=True",
    ]
    
    log_file = open(logs_dir / "jupyter.log", "w")
    subprocess.Popen(cmd, stdout=log_file, stderr=log_file)
    print("   ✅ JupyterLab started on port 8888")


def main():
    """Main entrypoint."""
    gpu_config = get_gpu_config(GPU_VARIANT)
    
    print("=" * 60)
    print(f"🚀 AiClipse ComfyUI - {TEMPLATE_NAME}")
    print(f"   GPU: {GPU_VARIANT} ({gpu_config.vram_gb}GB VRAM)")
    print("=" * 60)
    
    # Load config with env overrides
    config = Config.load(CONFIG_PATH)
    
    print(f"\n📋 Configuration:")
    print(f"   Template: {config.template.name} v{config.template.version}")
    print(f"   ComfyUI args: {' '.join(config.comfy_args)}")
    print(f"   Models: {len(config.get_all_models())}")
    print(f"   Nodes: {len(config.template.nodes)}")
    
    # Ensure directories exist
    MODELS_PATH.mkdir(parents=True, exist_ok=True)
    OUTPUTS_PATH.mkdir(parents=True, exist_ok=True)
    
    # Setup SSH
    setup_ssh()
    
    # Install custom nodes
    if config.template.nodes:
        node_specs = [{"repo": n.repo, "branch": n.branch or "main"} for n in config.template.nodes]
        install_custom_nodes(node_specs, COMFY_PATH)
    
    # Download models if needed
    if not config.skip_model_download:
        print("\n📦 Checking models...")
        
        # Check if models already exist
        downloader = ModelDownloader(config, MODELS_PATH)
        existing = sum(1 for m in config.get_all_models() 
                       if (MODELS_PATH / m.path / (Path(m.file or m.key or "").name)).exists())
        total = len(config.get_all_models())
        
        if existing < total:
            print(f"   Downloading {total - existing} missing model(s)...")
            downloader.download_all()
        else:
            print(f"   ✅ All {total} models present")
    else:
        print("\n⏭️  Skipping model download (SKIP_MODEL_DOWNLOAD=true)")
    
    # Setup model paths
    setup_model_paths(
        comfy_dir=COMFY_PATH,
        models_dir=MODELS_PATH,
        name="runpod_volume",
    )
    
    # Symlink outputs
    comfy_output = COMFY_PATH / "output"
    if comfy_output.exists() and not comfy_output.is_symlink():
        shutil.rmtree(comfy_output)
    if not comfy_output.exists():
        comfy_output.symlink_to(OUTPUTS_PATH)
        print(f"🔗 Outputs → {OUTPUTS_PATH}")
    
    # Start JupyterLab
    setup_jupyter()
    
    # Launch ComfyUI
    print("\n" + "=" * 60)
    print("🎨 Starting ComfyUI")
    print("=" * 60 + "\n")
    
    launcher = ComfyLauncher(config, comfy_dir=COMFY_PATH)
    launcher.run(blocking=True)


if __name__ == "__main__":
    main()
