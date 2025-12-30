"""
Configuration loading with environment variable overrides.

Hierarchy (highest priority first):
1. Environment variables (COMFY_ARGS, SKIP_MODEL_DOWNLOAD, etc.)
2. config.yaml values
3. Default values
"""

import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ModelSpec:
    """Specification for a model to download."""
    source: str  # huggingface, r2, civitai
    path: str    # Target subfolder in models/
    
    # HuggingFace
    repo: Optional[str] = None
    file: Optional[str] = None
    
    # R2
    key: Optional[str] = None
    
    # CivitAI
    model_id: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "ModelSpec":
        return cls(
            source=data["source"],
            path=data["path"],
            repo=data.get("repo"),
            file=data.get("file"),
            key=data.get("key"),
            model_id=data.get("model_id"),
        )


@dataclass
class NodeSpec:
    """Specification for a custom node to install."""
    repo: str
    branch: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "NodeSpec":
        if isinstance(data, str):
            return cls(repo=data)
        return cls(repo=data["repo"], branch=data.get("branch"))


@dataclass 
class TemplateConfig:
    """Configuration for a ComfyUI template."""
    name: str
    version: str
    description: str
    
    # ComfyUI settings
    comfy_version: str
    comfy_args: list[str]
    
    # Models and nodes
    models: list[ModelSpec]
    nodes: list[NodeSpec]
    
    # GPU requirements
    gpu_vram_gb: int
    recommended_gpus: list[str]
    
    @classmethod
    def from_dict(cls, data: dict) -> "TemplateConfig":
        return cls(
            name=data["name"],
            version=data["version"],
            description=data.get("description", ""),
            comfy_version=data.get("comfy", {}).get("version", "latest"),
            comfy_args=data.get("comfy", {}).get("args", []),
            models=[ModelSpec.from_dict(m) for m in data.get("models", [])],
            nodes=[NodeSpec.from_dict(n) for n in data.get("nodes", [])],
            gpu_vram_gb=int(data.get("gpu", {}).get("vram", "24GB").replace("GB", "")),
            recommended_gpus=data.get("gpu", {}).get("recommended", ["A10G"]),
        )


@dataclass
class Config:
    """
    Runtime configuration with environment overrides.
    
    Environment Variables:
        COMFY_ARGS: Override comfy args (space-separated)
        COMFY_VERSION: Override ComfyUI version
        SKIP_MODEL_DOWNLOAD: Skip model downloading (true/false)
        DOWNLOAD_MODELS: Enable model downloading (true/false)
        EXTRA_MODELS: Additional models to download (JSON)
        HF_TOKEN: HuggingFace API token
        R2_ACCESS_KEY_ID: R2 access key
        R2_SECRET_ACCESS_KEY: R2 secret key
        R2_BUCKET: R2 bucket name
        R2_ENDPOINT: R2 endpoint URL
    """
    template: TemplateConfig
    
    # Runtime overrides
    comfy_args: list[str] = field(default_factory=list)
    skip_model_download: bool = False
    extra_models: list[ModelSpec] = field(default_factory=list)
    
    # Credentials
    hf_token: Optional[str] = None
    r2_access_key: Optional[str] = None
    r2_secret_key: Optional[str] = None
    r2_bucket: Optional[str] = None
    r2_endpoint: Optional[str] = None
    
    @classmethod
    def load(cls, config_path: str | Path) -> "Config":
        """Load config from YAML with environment overrides."""
        path = Path(config_path)
        
        with open(path) as f:
            data = yaml.safe_load(f)
        
        template = TemplateConfig.from_dict(data)
        
        # === ENVIRONMENT OVERRIDES ===
        
        # COMFY_ARGS overrides config.yaml args
        env_args = os.environ.get("COMFY_ARGS")
        if env_args:
            comfy_args = env_args.split()
        else:
            comfy_args = template.comfy_args.copy()
        
        # COMFY_VERSION override
        env_version = os.environ.get("COMFY_VERSION")
        if env_version:
            template.comfy_version = env_version
        
        # Skip model download
        skip_download = (
            os.environ.get("SKIP_MODEL_DOWNLOAD", "").lower() == "true" or
            os.environ.get("DOWNLOAD_MODELS", "").lower() == "false"
        )
        
        # Extra models from env (JSON format)
        extra_models = []
        env_extra = os.environ.get("EXTRA_MODELS")
        if env_extra:
            import json
            extra_data = json.loads(env_extra)
            extra_models = [ModelSpec.from_dict(m) for m in extra_data]
        
        return cls(
            template=template,
            comfy_args=comfy_args,
            skip_model_download=skip_download,
            extra_models=extra_models,
            hf_token=os.environ.get("HF_TOKEN"),
            r2_access_key=os.environ.get("R2_ACCESS_KEY_ID"),
            r2_secret_key=os.environ.get("R2_SECRET_ACCESS_KEY"),
            r2_bucket=os.environ.get("R2_BUCKET"),
            r2_endpoint=os.environ.get("R2_ENDPOINT"),
        )
    
    def get_all_models(self) -> list[ModelSpec]:
        """Get all models (template + extra)."""
        return self.template.models + self.extra_models
    
    def get_comfy_launch_args(self) -> list[str]:
        """Get final ComfyUI launch arguments."""
        base_args = ["--listen", "0.0.0.0", "--port", "8188"]
        return base_args + self.comfy_args
