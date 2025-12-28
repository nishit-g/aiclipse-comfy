"""
Template Configuration Loader
==============================
Reads templates/*/config.yaml files - SAME format as RunPod.
Provides unified config for Modal deployment.

This ensures Modal uses the SAME configuration files as RunPod,
making template management unified across platforms.
"""
import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# =============================================================================
# Configuration Data Classes
# =============================================================================

@dataclass
class ModelConfig:
    """Model definition from config.yaml."""
    source: str  # huggingface, r2, civitai
    repo: str = ""
    file: str = ""
    path: str = ""
    key: str = ""  # For R2
    
    @classmethod
    def from_dict(cls, data: dict) -> "ModelConfig":
        return cls(
            source=data.get("source", "huggingface"),
            repo=data.get("repo", ""),
            file=data.get("file", ""),
            path=data.get("path", ""),
            key=data.get("key", ""),
        )


@dataclass
class NodeConfig:
    """Node definition from config.yaml."""
    repo: str
    branch: str = "main"
    
    @classmethod
    def from_dict(cls, data: dict) -> "NodeConfig":
        if isinstance(data, str):
            return cls(repo=data)
        return cls(
            repo=data.get("repo", ""),
            branch=data.get("branch", "main"),
        )


@dataclass 
class TemplateConfig:
    """Full template configuration from config.yaml."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    gpu_requirement: str = "24GB"
    comfy_args: list = field(default_factory=list)
    models: list = field(default_factory=list)
    nodes: list = field(default_factory=list)
    
    # Computed fields
    models_manifest_path: Optional[str] = None
    nodes_manifest_path: Optional[str] = None
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "TemplateConfig":
        """Load config from YAML file."""
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        
        config = cls(
            name=data.get("name", yaml_path.parent.name),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            gpu_requirement=data.get("gpu_requirement", "24GB"),
            comfy_args=data.get("comfy_args", []),
            models=[ModelConfig.from_dict(m) for m in data.get("models", [])],
            nodes=[NodeConfig.from_dict(n) for n in data.get("nodes", [])],
        )
        
        # Check for manifest files
        template_dir = yaml_path.parent
        models_manifest = template_dir / "models_manifest.txt"
        nodes_manifest = template_dir / "nodes_manifest.txt"
        
        if models_manifest.exists():
            config.models_manifest_path = str(models_manifest)
        if nodes_manifest.exists():
            config.nodes_manifest_path = str(nodes_manifest)
        
        return config


# =============================================================================
# GPU Mapping
# =============================================================================

GPU_REQUIREMENT_TO_MODAL = {
    "12GB": "T4",
    "16GB": "L4",
    "24GB": "A10G",
    "40GB": "A100",
    "48GB": "L40S",
    "80GB": "A100",
    # Named mappings
    "T4": "T4",
    "L4": "L4",
    "A10G": "A10G",
    "L40S": "L40S",
    "A100": "A100",
    "H100": "H100",
}


def get_modal_gpu(gpu_requirement: str) -> str:
    """Map config gpu_requirement to Modal GPU type."""
    return GPU_REQUIREMENT_TO_MODAL.get(gpu_requirement, "L40S")


# =============================================================================
# Template Loader
# =============================================================================

def get_templates_dir() -> Path:
    """Get the templates directory path."""
    # Try multiple locations
    candidates = [
        Path(__file__).parent.parent.parent / "templates",  # From modal/config/
        Path.cwd() / "templates",
        Path("/templates"),
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("Could not find templates directory")


def list_templates() -> list[str]:
    """List available template names."""
    templates_dir = get_templates_dir()
    return [
        d.name for d in templates_dir.iterdir()
        if d.is_dir() and (d / "config.yaml").exists()
    ]


def load_template_config(template_name: str) -> TemplateConfig:
    """Load configuration for a specific template."""
    templates_dir = get_templates_dir()
    config_path = templates_dir / template_name / "config.yaml"
    
    if not config_path.exists():
        # Fallback: check for manifests only (legacy templates)
        template_dir = templates_dir / template_name
        if template_dir.exists():
            return TemplateConfig(
                name=template_name,
                models_manifest_path=str(template_dir / "models_manifest.txt") if (template_dir / "models_manifest.txt").exists() else None,
                nodes_manifest_path=str(template_dir / "nodes_manifest.txt") if (template_dir / "nodes_manifest.txt").exists() else None,
            )
        raise FileNotFoundError(f"Template not found: {template_name}")
    
    return TemplateConfig.from_yaml(config_path)


def get_env_vars_for_template(config: TemplateConfig) -> dict:
    """
    Get environment variables to pass to start.sh.
    These are the SAME env vars RunPod uses!
    """
    env = {
        "TEMPLATE_TYPE": config.name,
        "TEMPLATE_VERSION": config.version,
        "DOWNLOAD_MODELS": "true",
    }
    
    # Manifest paths (for legacy scripts)
    if config.models_manifest_path:
        env["MODELS_MANIFEST"] = config.models_manifest_path
    if config.nodes_manifest_path:
        env["NODES_MANIFEST"] = config.nodes_manifest_path
    
    # ComfyUI arguments
    if config.comfy_args:
        env["COMFY_ARGS"] = " ".join(config.comfy_args)
    
    return env


# =============================================================================
# Main (for testing)
# =============================================================================

if __name__ == "__main__":
    print("Available templates:")
    for name in list_templates():
        config = load_template_config(name)
        print(f"  - {name} (GPU: {config.gpu_requirement}, Models: {len(config.models)}, Nodes: {len(config.nodes)})")
