import os
import sys
import subprocess
import concurrent.futures

# Configuration
MANIFEST_PATH = os.environ.get("NODES_MANIFEST", "/manifests/nodes.txt")
COMFY_DIR = os.environ.get("COMFY_DIR", "/workspace/aiclipse/ComfyUI")
NODES_DIR = os.path.join(COMFY_DIR, "custom_nodes")
UV_BIN = "/bin/uv"
VENV_PYTHON = "/venv/bin/python"

def log(msg, level="INFO"):
    print(f"[{level}] {msg}")

def run_cmd(cmd, cwd=None, env=None):
    try:
        subprocess.check_call(cmd, cwd=cwd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def install_node(line):
    parts = [p.strip() for p in line.split("|")]
    repo_url = parts[0]
    if not repo_url or repo_url.startswith("#"):
        return
    
    branch = parts[1] if len(parts) > 1 and parts[1] else "main"
    node_name = repo_url.split("/")[-1].replace(".git", "")
    target_path = os.path.join(NODES_DIR, node_name)
    
    if os.path.exists(target_path):
        log(f"Skipping {node_name} (already exists)")
        return

    log(f"Cloning {node_name} ({branch})...")
    
    # Clone
    if not run_cmd(["git", "clone", "--depth", "1", "-b", branch, repo_url, target_path]):
        # Fallback to default branch if specific branch fails
        log(f"Branch {branch} failed for {node_name}, trying default...", "WARN")
        if not run_cmd(["git", "clone", "--depth", "1", repo_url, target_path]):
             log(f"Failed to clone {node_name}", "ERROR")
             return

    # Install requirements using UV
    req_path = os.path.join(target_path, "requirements.txt")
    if os.path.exists(req_path):
        log(f"Installing requirements for {node_name}...")
        # Use uv pip install for speed
        # We target the main venv
        cmd = [UV_BIN, "pip", "install", "--no-cache-dir", "-r", req_path]
        # We need to ensure VIRTUAL_ENV is set or pass --python
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = "/venv"
        if not run_cmd(cmd, env=env):
             log(f"Failed to install requirements for {node_name}", "WARN")

    # Run install.py if exists
    install_py = os.path.join(target_path, "install.py")
    if os.path.exists(install_py):
        log(f"Running install.py for {node_name}...")
        run_cmd([VENV_PYTHON, "install.py"], cwd=target_path)

def main():
    if not os.path.exists(MANIFEST_PATH):
        log(f"Manifest not found at {MANIFEST_PATH}", "WARN")
        return

    log(f"Installing nodes from {MANIFEST_PATH}...")
    
    if not os.path.exists(NODES_DIR):
        os.makedirs(NODES_DIR)

    with open(MANIFEST_PATH, "r") as f:
        lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]

    # Parallel installation
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(install_node, lines)

    log("Node installation complete.")

if __name__ == "__main__":
    main()
