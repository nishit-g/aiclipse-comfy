# 🎨 Creating New Templates - Developer Guide

This guide shows you how to create a new ComfyUI template for the AiClipse system.

## 🚀 Quick Start - Add Your Template

### Step 1: Create Template Directory

```bash
# Create your template directory
mkdir templates/my-workflow
cd templates/my-workflow
```

### Step 2: Create Models Manifest

Create `models_manifest.txt` with your required models:

```txt
# My Workflow Template Models
# Format: repo_id|filename|target_subdir

# Your specific models
runwayml/stable-diffusion-v1-5|v1-5-pruned-emaonly.safetensors|checkpoints
stabilityai/sd-vae-ft-mse-original|vae-ft-mse-840000-ema-pruned.safetensors|vae

# Add more models as needed
your-username/custom-model|model.safetensors|checkpoints
```

### Step 3: Create Custom Nodes Manifest

Create `nodes_manifest.txt` for template-specific nodes:

```txt
# My Workflow Custom Nodes
# Format: repo_url|branch|category|description

# Essential nodes for your workflow
https://github.com/your-favorite/comfyui-node|main|custom|Description
https://github.com/another/useful-node|main|utility|Another description

# Include base nodes (optional)
# The system will automatically use /manifests/base_nodes.txt for common nodes
```

### Step 4: Create Workflows Directory

```bash
# Create workflows directory
mkdir workflows

# Add your ComfyUI workflow JSON files
# Example: workflows/basic_generation.json
# Example: workflows/advanced_processing.json
```

### Step 5: Create Template Dockerfile

Create `Dockerfile`:

```dockerfile
ARG BASE_IMAGE=ghcr.io/nishit-g/aiclipse-base-rtx4090:latest
FROM ${BASE_IMAGE}

ENV TEMPLATE_TYPE="my-workflow"
ENV TEMPLATE_VERSION="1.0.0"
ENV DOWNLOAD_MODELS=true

# Copy template-specific model manifest
COPY models_manifest.txt /manifests/my_workflow_models.txt

# Copy custom nodes manifest (optional - if you have template-specific nodes)
COPY nodes_manifest.txt /manifests/my_workflow_nodes.txt

# Copy workflows
COPY workflows/ /opt/workflows/

# Set environment to point to manifests
ENV MODELS_MANIFEST="/manifests/my_workflow_models.txt"
ENV NODES_MANIFEST="/manifests/my_workflow_nodes.txt"

CMD ["/scripts/start.sh"]
```

### Step 6: Add Build Configuration

Update `docker-bake.hcl` to include your template:

```hcl
# Add this to docker-bake.hcl

# My Workflow Template builds
target "my-workflow-4090" {
    dockerfile = "templates/my-workflow/Dockerfile"
    args = {
        BASE_IMAGE = "${REGISTRY}/aiclipse-base-rtx4090:${VERSION}"
    }
    tags = ["${REGISTRY}/aiclipse-my-workflow:rtx4090-${VERSION}"]
    platforms = ["linux/amd64"]
    depends_on = ["base-rtx4090"]
}

target "my-workflow-5090" {
    dockerfile = "templates/my-workflow/Dockerfile"
    args = {
        BASE_IMAGE = "${REGISTRY}/aiclipse-base-rtx5090:${VERSION}"
    }
    tags = ["${REGISTRY}/aiclipse-my-workflow:rtx5090-${VERSION}"]
    platforms = ["linux/amd64"]
    depends_on = ["base-rtx5090"]
}

# Add to build groups
group "my-workflow" {
    targets = ["my-workflow-4090", "my-workflow-5090"]
}

# Update the "all" group
group "all" {
    targets = ["bases", "headshots", "my-workflow"]  # Add your template here
}
```

### Step 7: Build Your Template

```bash
# Build your template
./scripts/build.sh my-workflow

# Or build everything
./scripts/build.sh all
```

### Step 8: Test Your Template

```bash
# Test locally
docker run -p 8188:8188 -p 8080:8080 \
  ghcr.io/nishit-g/aiclipse-my-workflow:rtx4090-latest

# Check logs
docker logs <container-id>
```

## 📁 Template Structure Example

```
templates/my-workflow/
├── Dockerfile                 # Template definition
├── models_manifest.txt        # Required models
├── nodes_manifest.txt         # Custom nodes (optional)
├── workflows/                 # ComfyUI workflows
│   ├── basic_generation.json
│   ├── advanced_processing.json
│   └── batch_processing.json
└── README.md                  # Template documentation
```

## 🎯 Template Categories

### Workflow-Based Templates
- **Purpose**: Specific creative workflows
- **Examples**: Headshots, Product Photography, Logo Design
- **Focus**: Models + Nodes + Workflows for specific use case

### Technique-Based Templates
- **Purpose**: Specific AI techniques
- **Examples**: ControlNet, LoRA Training, Upscaling
- **Focus**: Specialized nodes and models for techniques

### Industry-Based Templates
- **Purpose**: Industry-specific solutions
- **Examples**: Real Estate, Fashion, Gaming
- **Focus**: Workflows tailored to industry needs

## ⚙️ Advanced Configuration

### Environment Variables

Add template-specific environment variables:

```dockerfile
# In your Dockerfile
ENV TEMPLATE_DESCRIPTION="My amazing workflow for X"
ENV RECOMMENDED_VRAM="12GB"
ENV SPECIALTY_FEATURES="feature1,feature2,feature3"
```

### Custom Initialization

Create template-specific setup scripts:

```bash
# templates/my-workflow/scripts/setup_my_workflow.sh
#!/bin/bash
setup_my_workflow() {
    log "🎨 Setting up My Workflow template..."

    # Custom setup logic here
    # Example: Download additional resources
    # Example: Configure specific settings

    log "✅ My Workflow setup complete"
}
```

### Workflow Metadata

Add metadata to your workflows:

```json
{
  "workflow_info": {
    "name": "Basic Generation",
    "description": "Simple image generation workflow",
    "author": "Your Name",
    "version": "1.0.0",
    "tags": ["basic", "generation", "stable-diffusion"]
  },
  "nodes": {
    // Your ComfyUI workflow nodes here
  }
}
```

## 🔧 Build System Integration

### Build Scripts

Update build scripts to handle your template:

```bash
# In scripts/build.sh, this is already handled by the case statement
# Your template will work automatically if you follow the naming convention
```

### Testing Integration

Add your template to testing:

```bash
# Add to scripts/test.sh (if you create one)
case $TARGET in
    "my-workflow")
        echo "🧪 Testing my-workflow template..."
        docker run --rm ghcr.io/nishit-g/aiclipse-my-workflow:rtx4090-latest /scripts/health-check.sh
        ;;
esac
```

## 📋 Best Practices

### 1. **Naming Conventions**
- Template directory: `templates/my-workflow`
- Docker tags: `aiclipse-my-workflow:rtx4090-latest`
- Manifest files: `my_workflow_models.txt`

### 2. **Model Selection**
- Only include models you actually need
- Prefer smaller, efficient models when possible
- Document model purposes in comments

### 3. **Node Selection**
- Start with base nodes from `/manifests/base_nodes.txt`
- Add only template-specific nodes
- Test node compatibility

### 4. **Workflow Organization**
- Name workflows descriptively
- Include workflow metadata
- Provide example inputs

### 5. **Documentation**
- Create template README.md
- Document usage examples
- List requirements and recommendations

## 🚀 Deployment

### RunPod Template Creation

1. **Build and push your template**
2. **Create RunPod template** with:
   - Container Image: `ghcr.io/nishit-g/aiclipse-my-workflow:rtx4090-latest`
   - Exposed Ports: `22, 8188, 8080, 8888, 8048`
   - Volume Mount: `/workspace`

### Environment Variables for RunPod

```bash
TEMPLATE_TYPE=my-workflow
DOWNLOAD_MODELS=true
PUBLIC_KEY=your-ssh-public-key
HF_TOKEN=your-huggingface-token
```

## 🔍 Troubleshooting

### Common Issues

**Build fails:**
```bash
# Check Dockerfile syntax
docker build -f templates/my-workflow/Dockerfile .

# Check dependencies
./scripts/configure.sh
```

**Models not downloading:**
```bash
# Check manifest format
# Verify HuggingFace token
# Check logs: /workspace/aiclipse/logs/models.log
```

**Nodes not loading:**
```bash
# Check node manifest format
# Verify repository URLs
# Check ComfyUI logs for import errors
```

## 📞 Getting Help

- **GitHub Issues**: [Report problems](https://github.com/nishit-g/aiclipse-comfyui/issues)
- **Documentation**: Check existing templates for examples
- **Community**: Join our Discord for template development help

---

**Happy template building!** 🎉
