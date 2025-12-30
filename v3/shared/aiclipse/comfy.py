"""
ComfyUI launcher utilities.
"""

import os
import subprocess
import signal
from pathlib import Path
from typing import Optional

from .config import Config
from .paths import setup_model_paths


class ComfyLauncher:
    """Launch and manage ComfyUI process."""
    
    def __init__(
        self,
        config: Config,
        comfy_dir: Optional[str | Path] = None,
    ):
        self.config = config
        self.comfy_dir = Path(comfy_dir) if comfy_dir else self._find_comfy_dir()
        self.process: Optional[subprocess.Popen] = None
    
    def _find_comfy_dir(self) -> Path:
        """Find ComfyUI installation directory."""
        # Check common locations
        candidates = [
            Path("/root/comfy"),  # comfy-cli default
            Path("/workspace/aiclipse/ComfyUI"),  # Legacy
            Path.home() / "comfy",
            Path.cwd() / "ComfyUI",
        ]
        
        for path in candidates:
            if (path / "main.py").exists():
                return path
        
        raise FileNotFoundError("ComfyUI installation not found")
    
    def setup_model_paths(self, models_dir: str | Path) -> Path:
        """Configure model paths for ComfyUI."""
        return setup_model_paths(
            comfy_dir=self.comfy_dir,
            models_dir=models_dir,
            name="aiclipse",
        )
    
    def get_launch_command(self) -> list[str]:
        """Get the command to launch ComfyUI."""
        args = self.config.get_comfy_launch_args()
        
        # Use comfy-cli if available
        if self._has_comfy_cli():
            return ["comfy", "launch", "--"] + args
        else:
            return ["python", "main.py"] + args
    
    def _has_comfy_cli(self) -> bool:
        """Check if comfy-cli is installed."""
        try:
            result = subprocess.run(
                ["comfy", "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def run(self, blocking: bool = True) -> Optional[subprocess.Popen]:
        """
        Run ComfyUI.
        
        Args:
            blocking: If True, wait for process to exit. If False, return Popen.
        """
        cmd = self.get_launch_command()
        
        print(f"\n🖥️  Running: {' '.join(cmd)}")
        print(f"   Directory: {self.comfy_dir}")
        print()
        
        # Change to ComfyUI directory
        os.chdir(self.comfy_dir)
        
        if blocking:
            # Replace current process (exec)
            os.execvp(cmd[0], cmd)
        else:
            # Run in background
            self.process = subprocess.Popen(
                cmd,
                cwd=self.comfy_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            return self.process
    
    def stop(self) -> None:
        """Stop ComfyUI if running in background."""
        if self.process:
            self.process.send_signal(signal.SIGTERM)
            self.process.wait(timeout=10)
            self.process = None


def install_comfy_cli(cuda_version: str = "12.4") -> None:
    """Install ComfyUI using comfy-cli."""
    print("📦 Installing ComfyUI via comfy-cli...")
    
    subprocess.run(
        ["comfy", "--skip-prompt", "install", f"--cuda-version={cuda_version}"],
        check=True,
    )
    
    print("✅ ComfyUI installed")


def install_custom_nodes(
    nodes: list[dict],
    comfy_dir: Path,
    max_parallel: int = 10,
) -> dict[str, bool]:
    """
    Install custom nodes in parallel with retry logic.
    
    Args:
        nodes: List of node specs from config.yaml
        comfy_dir: ComfyUI installation directory
        max_parallel: Maximum parallel installations
    
    Returns:
        Dict of {node_name: success}
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    custom_nodes_dir = comfy_dir / "custom_nodes"
    custom_nodes_dir.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    def install_single_node(node_spec: dict) -> tuple[str, bool, str]:
        """Install a single node. Returns (name, success, message)."""
        repo = node_spec.get("repo") if isinstance(node_spec, dict) else node_spec
        branch = node_spec.get("branch", "main") if isinstance(node_spec, dict) else "main"
        
        name = repo.split("/")[-1].replace(".git", "")
        target = custom_nodes_dir / name
        
        # Skip if exists
        if target.exists():
            return (name, True, "exists")
        
        # Retry logic (3 attempts)
        for attempt in range(1, 4):
            try:
                result = subprocess.run(
                    ["git", "clone", "--depth", "1", "-b", branch, repo, str(target)],
                    capture_output=True,
                    timeout=120,
                )
                
                if result.returncode == 0:
                    # Install requirements if present
                    req_file = target / "requirements.txt"
                    if req_file.exists():
                        subprocess.run(
                            ["pip", "install", "-q", "-r", str(req_file)],
                            capture_output=True,
                            timeout=300,
                        )
                    
                    # Run install.py if present
                    install_script = target / "install.py"
                    if install_script.exists():
                        subprocess.run(
                            ["python", str(install_script)],
                            capture_output=True,
                            cwd=target,
                            timeout=300,
                        )
                    
                    return (name, True, "installed")
                    
            except subprocess.TimeoutExpired:
                pass
            except Exception as e:
                if attempt == 3:
                    return (name, False, str(e))
            
            if attempt < 3:
                import time
                time.sleep(2)
        
        return (name, False, "failed after 3 attempts")
    
    if not nodes:
        return results
    
    print(f"\n📦 Installing {len(nodes)} custom node(s) (max {max_parallel} parallel)...")
    
    with ThreadPoolExecutor(max_workers=max_parallel) as executor:
        futures = {executor.submit(install_single_node, node): node for node in nodes}
        
        for future in as_completed(futures):
            name, success, message = future.result()
            results[name] = success
            
            if success:
                if message == "exists":
                    print(f"   ⏭️  {name} (exists)")
                else:
                    print(f"   ✅ {name}")
            else:
                print(f"   ❌ {name}: {message}")
    
    installed = sum(1 for v in results.values() if v)
    print(f"✅ Custom nodes: {installed}/{len(nodes)} installed")
    
    return results
