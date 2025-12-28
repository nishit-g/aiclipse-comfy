# ComfyUI Production API Documentation

A complete, production-ready ComfyUI deployment on Modal with WebSocket streaming, real-time progress tracking, and enterprise features.

## 📚 Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [WebSocket Protocol](#websocket-protocol)
- [Model Management](#model-management)
- [Workflow Management](#workflow-management)
- [Deployment Guide](#deployment-guide)
- [Development Guide](#development-guide)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)

## 🎯 Overview

This ComfyUI implementation provides:

- **Real-time WebSocket API** with live progress updates
- **Memory snapshots** for 10x faster cold starts
- **Multi-source model downloads** (HuggingFace, Civitai, URLs)
- **Production-grade error handling** and logging
- **Developer-friendly CLI** for management
- **Interactive UI** for workflow development
- **R2/S3 output support** for scalable storage

### Key Features

✅ **Fast Cold Starts** - Memory snapshots reduce startup time from 60s to 5s
✅ **Real-time Progress** - See exactly what's happening during generation
✅ **Auto-scaling** - Handles traffic spikes automatically
✅ **Error Recovery** - Graceful handling of failures
✅ **Multi-tenancy** - Concurrent users without interference
✅ **Cost Optimized** - Pay only for actual usage

## 🚀 Quick Start

### 1. Initial Setup

```bash
# Clone or create your project directory
mkdir comfyui-api && cd comfyui-api

# Install Modal CLI
pip install modal

# Authenticate with Modal
modal auth new

# Create configuration templates
modal run comfy_app.py::create_config_templates
```

### 2. Configure Your Setup

Edit the generated configuration files:

**`config/models.yaml`** - Define your models:
```yaml
flux-schnell:
  type: "checkpoints"
  source: "huggingface"
  repo_id: "Comfy-Org/flux1-schnell"
  filename: "flux1-schnell-fp8.safetensors"

realistic-vision:
  type: "checkpoints"
  source: "civitai"
  model_id: "4201"
```

**`config/custom_nodes.json`** - Define custom nodes:
```json
[
  {
    "name": "was-node-suite-comfyui",
    "description": "WAS Node Suite - Essential image processing"
  },
  {
    "name": "ComfyUI-Impact-Pack",
    "description": "Face enhancement and segmentation"
  }
]
```

**`workflows/`** - Add your ComfyUI workflow JSON files exported with "Save (API format)"

### 3. Deploy and Initialize

```bash
# Deploy to Modal
modal deploy comfy_app.py

# Download models (this takes time for large models)
modal run comfy_app.py::main --mode download

# Sync workflows to persistent storage
modal run comfy_app.py::main --mode sync

# Test the deployment
modal run comfy_app.py::test_websocket
```

### 4. Access Your API

```bash
# Get deployment URLs
modal run comfy_app.py::main --mode info

# Outputs:
# 📡 API URL: https://your-username--comfyui-production-api-api.modal.run
# 🎨 UI URL: https://your-username--comfyui-production-api-ui.modal.run
```

## 🏗️ Architecture

### Component Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client App    │───▶│  FastAPI + WS   │───▶│  ComfyUI Core   │
│  (Web/Mobile)   │    │   (Modal Fn)    │    │ (Memory Cached) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Persistent Vol. │    │   GPU Memory    │
                       │ Models/Workflows│    │ Loaded Models   │
                       └─────────────────┘    └─────────────────┘
```

### Modal Architecture Pattern

```python
# BUILD TIME (Image Creation)
Image.debian_slim()
  .pip_install(dependencies)
  .run_function(install_comfyui)  # Core software only

# RUNTIME - Pre-Snapshot (Cached)
@modal.enter(snap=True)
def setup_pre_snapshot():
    install_custom_nodes()  # Heavy operations, cached

# RUNTIME - Post-Snapshot (Fast)
@modal.enter(snap=False)
def setup_post_snapshot():
    start_comfyui_server()  # Light operations, each start
```

### Scaling Strategy

- **Container Lifecycle**: 10-minute idle timeout for cost optimization
- **Concurrency**: 10 concurrent requests per container
- **GPU Selection**: Configurable (L4, A10G, L40S, A100, H100)
- **Memory Snapshots**: Pre-loaded state for instant scaling
- **Volume Persistence**: Models and workflows survive container restarts

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in your project root:

```bash
# Required
DEFAULT_GPU=L4                    # L4, A10G, L40S, A100, H100
COMFYUI_VERSION=0.3.41           # ComfyUI version to install

# Optional - For Civitai models
CIVITAI_API_KEY=your_api_key_here

# Optional - For R2/S3 output
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=auto
R2_ENDPOINT_URL=https://account.r2.cloudflarestorage.com
```

### Model Configuration

**`config/models.yaml`** supports multiple sources:

#### HuggingFace Models
```yaml
flux-dev:
  type: "checkpoints"           # checkpoints, loras, vae, controlnet, etc.
  source: "huggingface"
  repo_id: "black-forest-labs/FLUX.1-dev"
  filename: "flux1-dev.safetensors"
```

#### Civitai Models
```yaml
realistic-vision:
  type: "checkpoints"
  source: "civitai"
  model_id: "4201"              # Model ID from Civitai URL
  # Optional: version_id, file_id for specific versions
```

#### Direct URLs
```yaml
custom-model:
  type: "checkpoints"
  source: "url"
  url: "https://example.com/model.safetensors"
  filename: "custom-model.safetensors"  # Optional
```

### Custom Nodes Configuration

**`config/custom_nodes.json`**:

```json
[
  {
    "name": "was-node-suite-comfyui",
    "description": "WAS Node Suite - Essential utilities"
  },
  {
    "name": "ComfyUI-Manager",
    "description": "Node package manager"
  },
  {
    "name": "ComfyUI-Impact-Pack",
    "description": "Face enhancement tools"
  },
  {
    "name": "ComfyUI-AnimateDiff-Evolved",
    "description": "Animation and video generation"
  }
]
```

## 📡 API Reference

### Base URL
```
https://your-username--comfyui-production-api-api.modal.run
```

### Authentication
No authentication required for this implementation. Add API keys or OAuth as needed for production.

### Endpoints

#### `GET /`
Root endpoint with API information.

**Response:**
```json
{
  "message": "ComfyUI Production API",
  "endpoints": {
    "websocket": "/api/v1/generate",
    "rest": "/api/v1/generate",
    "workflows": "/api/v1/workflows",
    "models": "/api/v1/models",
    "health": "/health"
  },
  "docs": "/docs"
}
```

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "comfyui-production-api",
  "version": "1.0.0"
}
```

#### `GET /api/v1/workflows`
List available workflows.

**Response:**
```json
{
  "workflows": ["txt2img", "img2img", "controlnet"]
}
```

#### `GET /api/v1/models`
List available models by type.

**Response:**
```json
{
  "models": {
    "checkpoints": ["flux1-schnell-fp8.safetensors", "realisticVision.safetensors"],
    "loras": ["style-lora.safetensors"],
    "controlnet": ["canny-controlnet.safetensors"]
  }
}
```

#### `POST /api/v1/generate`
Simple REST endpoint for workflow execution (no streaming).

**Request:**
```json
{
  "workflow_id": "txt2img",
  "params": {
    "text": "a beautiful landscape",
    "6.text": "a beautiful landscape",
    "steps": 20,
    "cfg": 7.0,
    "width": 1024,
    "height": 1024,
    "seed": 123456
  },
  "output": {
    "bucket": "my-bucket",
    "path": "generated/user-123/",
    "endpoint_url": "https://account.r2.cloudflarestorage.com"
  }
}
```

**Response:**
```json
{
  "status": "queued",
  "prompt_id": "abc123-def456-789"
}
```

## 🔌 WebSocket Protocol

### Connection
```javascript
const ws = new WebSocket('wss://your-app.modal.run/api/v1/generate');
```

### Request Format
Send JSON request after connection opens:
```json
{
  "workflow_id": "txt2img",
  "params": {
    "text": "a beautiful landscape painting",
    "6.text": "a beautiful landscape painting",
    "steps": 20,
    "cfg": 7.0,
    "width": 1024,
    "height": 1024
  },
  "client_id": "optional-client-id"
}
```

### Response Messages

#### Status Updates
```json
{
  "status": "starting",
  "message": "Loading workflow..."
}
```

```json
{
  "status": "queued",
  "prompt_id": "abc123",
  "message": "Workflow queued for execution"
}
```

```json
{
  "status": "running",
  "prompt_id": "abc123",
  "progress": 0.45,
  "current_step": 9,
  "total_steps": 20,
  "current_node": "KSampler",
  "message": "Sampling: 9/20"
}
```

#### Results
```json
{
  "status": "result",
  "result_type": "base64",
  "result_data": "iVBORw0KGgoAAAANSUhEUgAA...",
  "filename": "ComfyUI_00001_.png"
}
```

```json
{
  "status": "result",
  "result_type": "url",
  "result_data": "s3://my-bucket/generated/image.png",
  "filename": "image.png"
}
```

#### Completion
```json
{
  "status": "completed",
  "prompt_id": "abc123",
  "message": "Generated 1 images successfully"
}
```

#### Errors
```json
{
  "status": "error",
  "error": "Workflow 'invalid.json' not found"
}
```

### Parameter Mapping

Parameters can target specific nodes or use common names:

```json
{
  "params": {
    // Specific node targeting (recommended)
    "6.text": "positive prompt",     // Node 6, text input
    "7.text": "negative prompt",    // Node 7, text input
    "3.steps": 25,                 // Node 3, steps input
    "3.cfg": 8.0,                 // Node 3, cfg input
    "5.width": 1024,               // Node 5, width input
    "5.height": 1024,              // Node 5, height input

    // Common name matching (searches all nodes)
    "text": "fallback prompt",      // Matches any 'text' input
    "steps": 20,                   // Matches any 'steps' input
    "cfg": 7.0                     // Matches any 'cfg' input
  }
}
```

## 🎨 Model Management

### Downloading Models

```bash
# Download all models from config
modal run comfy_app.py::main --mode download

# Check download progress in logs
modal logs list
```

### Supported Sources

#### 1. HuggingFace
```yaml
model-name:
  type: "checkpoints"
  source: "huggingface"
  repo_id: "author/model-name"
  filename: "model.safetensors"
  # Optional: revision: "main"
```

#### 2. Civitai
```yaml
model-name:
  type: "checkpoints"
  source: "civitai"
  model_id: "4201"
  # Optional: version_id, file_id for specific versions
```

**Getting Civitai Model ID:**
1. Go to model page: `https://civitai.com/models/4201/realistic-vision-v60-b1`
2. Model ID is the number after `/models/`: `4201`

#### 3. Direct URLs
```yaml
model-name:
  type: "checkpoints"
  source: "url"
  url: "https://example.com/model.safetensors"
  filename: "model.safetensors"  # Optional, extracted from URL if not provided
```

### Model Types

Supported model types that map to ComfyUI directories:

- `checkpoints` → `/models/checkpoints/`
- `loras` → `/models/loras/`
- `vae` → `/models/vae/`
- `controlnet` → `/models/controlnet/`
- `embeddings` → `/models/embeddings/`
- `clip_vision` → `/models/clip_vision/`
- `ipadapter` → `/models/ipadapter/`

### Model Storage

Models are stored in persistent Modal volumes:
- **Volume**: `comfyui-models`
- **Mount Path**: `/mnt/models/`
- **ComfyUI Path**: `/root/comfy/ComfyUI/models/` (symlinked)
- **Cache**: HuggingFace cache in `/cache/` volume

## 📋 Workflow Management

### Creating Workflows

1. **Use the Development UI:**
   ```bash
   modal run comfy_app.py::main --mode ui
   ```

2. **Create your workflow** in the ComfyUI interface

3. **Export as API format:**
   - Enable "Dev mode options" in settings
   - Use "Save (API format)" button
   - Save as `.json` file in `workflows/` directory

4. **Sync to deployment:**
   ```bash
   modal run comfy_app.py::main --mode sync
   ```

### Workflow Structure

ComfyUI API workflows are JSON objects where each key is a node ID:

```json
{
  "3": {
    "inputs": {
      "seed": 123456,
      "steps": 20,
      "cfg": 7.0,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1.0,
      "model": ["4", 0],        // Reference to node 4, output 0
      "positive": ["6", 0],     // Reference to node 6, output 0
      "negative": ["7", 0],     // Reference to node 7, output 0
      "latent_image": ["5", 0]  // Reference to node 5, output 0
    },
    "class_type": "KSampler"
  },
  "4": {
    "inputs": {
      "ckpt_name": "flux1-schnell-fp8.safetensors"
    },
    "class_type": "CheckpointLoaderSimple"
  }
  // ... more nodes
}
```

### Parameterizing Workflows

Make workflows dynamic by using the API's parameter injection:

```json
// Original workflow node
"6": {
  "inputs": {
    "text": "a beautiful landscape",  // This will be replaced
    "clip": ["4", 1]
  },
  "class_type": "CLIPTextEncode"
}
```

```python
# API request to override the text
{
  "workflow_id": "txt2img",
  "params": {
    "6.text": "a cyberpunk cityscape"  // Replaces node 6's text input
  }
}
```

## 🚀 Deployment Guide

### Prerequisites

- [Modal CLI](https://modal.com/docs/getting-started) installed and authenticated
- Python 3.11+
- Local ComfyUI workflows exported as JSON

### Production Deployment

#### 1. Environment Setup
```bash
# Create project directory
mkdir comfyui-production && cd comfyui-production

# Set up Modal authentication
modal auth new --profile production

# Create environment configuration
cp .env.example .env
# Edit .env with your settings
```

#### 2. Configuration
```bash
# Generate config templates
modal run comfy_app.py::create_config_templates

# Customize for your needs
vim config/models.yaml        # Add your models
vim config/custom_nodes.json  # Add required custom nodes
cp /path/to/workflows/*.json workflows/  # Add your workflows
```

#### 3. Deploy and Initialize
```bash
# Deploy the application
modal deploy comfy_app.py

# Download models (can take 30-60 minutes for large models)
modal run comfy_app.py::main --mode download

# Sync workflows
modal run comfy_app.py::main --mode sync

# Verify deployment
modal run comfy_app.py::main --mode info
```

#### 4. Testing
```bash
# Test WebSocket API
modal run comfy_app.py::test_websocket

# Test specific workflow
modal run comfy_app.py::main --mode test --workflow txt2img --prompt "test image"
```

### Scaling Configuration

Edit the deployment for your traffic needs:

```python
@app.cls(
    gpu="L40S",                    # Upgrade GPU for better performance
    container_idle_timeout=1800,   # 30 min for high-traffic apps
    allow_concurrent_inputs=20,     # More concurrent requests
    max_containers=10,              # Maximum container count
)
```

### Monitoring

Monitor your deployment:

```bash
# View logs
modal logs list
modal logs follow your-app-name

# View container stats
modal stats your-app-name

# View volume usage
modal volume list
```

## 🔧 Development Guide

### Local Development

#### 1. Setup Development Environment
```bash
# Install dependencies
pip install modal python-dotenv pyyaml

# Set up development configuration
cp .env.example .env.dev
```

#### 2. Iterative Development
```bash
# Start development UI
modal run comfy_app.py::main --mode ui

# Make changes to workflows in the UI
# Export and save to workflows/ directory

# Test changes
modal run comfy_app.py::test_websocket --workflow_id your_workflow

# Deploy updates
modal run comfy_app.py::main --mode sync
```

#### 3. Adding New Models
```yaml
# Add to config/models.yaml
new-model:
  type: "checkpoints"
  source: "huggingface"
  repo_id: "author/model"
  filename: "model.safetensors"
```

```bash
# Download new models
modal run comfy_app.py::main --mode download
```

#### 4. Adding Custom Nodes
```json
// Add to config/custom_nodes.json
{
  "name": "new-custom-node",
  "description": "Description of functionality"
}
```

```bash
# Redeploy to install new nodes
modal deploy comfy_app.py
```

### Code Structure

```
comfy_app.py                 # Main application file
├── Configuration           # Environment and settings
├── Modal App Setup         # Volume, secrets, image definition
├── ComfyUIService         # Core service class
│   ├── Pre-snapshot setup  # Custom nodes installation
│   ├── Post-snapshot setup # Server startup
│   └── Workflow execution  # WebSocket streaming logic
├── Management Functions    # Model downloads, workflow sync
├── API Endpoints          # FastAPI application
├── Development UI         # Interactive ComfyUI
└── CLI Entrypoints       # Management commands

config/
├── models.yaml            # Model definitions
└── custom_nodes.json     # Custom node list

workflows/
├── txt2img.json          # Text-to-image workflow
├── img2img.json          # Image-to-image workflow
└── controlnet.json       # ControlNet workflow
```

### Best Practices

#### Performance Optimization
- Use **memory snapshots** for faster cold starts
- Set appropriate **container idle timeout** based on usage patterns
- Configure **concurrent inputs** based on GPU memory
- Use **L4/A10G** for cost efficiency, **L40S/A100** for performance

#### Error Handling
- Always wrap API calls in try-catch blocks
- Provide meaningful error messages to users
- Log errors with context for debugging
- Implement retry logic for transient failures

#### Security
- Use Modal Secrets for sensitive configuration
- Validate all user inputs
- Implement rate limiting for production use
- Add authentication/authorization as needed

## 🔍 Troubleshooting

### Common Issues

#### 1. "Workflow not found" Error
**Problem:** `FileNotFoundError: Workflow 'xyz.json' not found`

**Solution:**
```bash
# Check available workflows
modal run comfy_app.py::main --mode info
# Sync workflows if missing
modal run comfy_app.py::main --mode sync
```

#### 2. Model Loading Failures
**Problem:** Models not loading in ComfyUI

**Solutions:**
```bash
# Verify models downloaded
modal logs list | grep download

# Check model volume contents
modal volume ls comfyui-models

# Re-download if needed
modal run comfy_app.py::main --mode download
```

#### 3. Custom Node Installation Failures
**Problem:** Custom nodes not working

**Solutions:**
```bash
# Check installation logs
modal logs list | grep "custom node"

# Verify node names in ComfyUI Registry
# https://registry.comfy.org/

# Update config/custom_nodes.json with correct names
# Redeploy
modal deploy comfy_app.py
```

#### 4. WebSocket Connection Issues
**Problem:** WebSocket connections failing

**Solutions:**
```bash
# Test basic connectivity
curl https://your-app.modal.run/health

# Check server logs
modal logs follow your-app-name

# Verify WebSocket URL format
wss://your-app.modal.run/api/v1/generate  # ✅ Correct
ws://your-app.modal.run/api/v1/generate   # ❌ Wrong (use wss)
```

#### 5. GPU Memory Issues
**Problem:** Out of memory errors during generation

**Solutions:**
```python
# Reduce concurrent inputs
@app.cls(allow_concurrent_inputs=5)  # Lower number

# Upgrade GPU
@app.cls(gpu="A100")  # More VRAM

# Optimize workflow parameters
{
  "params": {
    "width": 512,   # Smaller resolution
    "height": 512,
    "steps": 20     # Fewer steps
  }
}
```

### Debugging Tips

#### Enable Verbose Logging
```python
# In your code
logger.setLevel(logging.DEBUG)
```

#### Monitor Resource Usage
```bash
# View container stats
modal stats your-app-name

# Monitor GPU usage
modal logs follow your-app-name | grep GPU
```

#### Test Components Individually
```bash
# Test model downloads only
modal run comfy_app.py::main --mode download

# Test workflow sync only
modal run comfy_app.py::main --mode sync

# Test API without WebSocket
curl -X POST https://your-app.modal.run/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"workflow_id":"txt2img","params":{"text":"test"}}'
```

### Performance Issues

#### Slow Cold Starts
- Ensure memory snapshots are enabled
- Minimize custom node installations
- Use smaller base models during development

#### High Latency
- Check GPU selection (upgrade if needed)
- Reduce image resolution for testing
- Optimize workflow complexity

#### Cost Optimization
- Set appropriate idle timeouts
- Use spot instances for development
- Monitor usage patterns and adjust scaling

## 📋 Examples

### Python Client

```python
import asyncio
import websockets
import json
import base64
from pathlib import Path

async def generate_image():
    uri = "wss://your-app.modal.run/api/v1/generate"

    request = {
        "workflow_id": "txt2img",
        "params": {
            "text": "a beautiful mountain landscape at sunset",
            "6.text": "a beautiful mountain landscape at sunset",
            "steps": 25,
            "cfg": 7.5,
            "width": 1024,
            "height": 1024
        }
    }

    async with websockets.connect(uri) as websocket:
        # Send request
        await websocket.send(json.dumps(request))

        # Receive updates
        async for message in websocket:
            data = json.loads(message)
            status = data.get("status")

            if status == "running":
                progress = data.get("progress", 0)
                print(f"Progress: {progress:.1%}")

            elif status == "result":
                # Save base64 image
                image_data = base64.b64decode(data["result_data"])
                filename = data.get("filename", "generated.png")
                Path(filename).write_bytes(image_data)
                print(f"Saved: {filename}")

            elif status == "completed":
                print("Generation completed!")
                break

            elif status == "error":
                print(f"Error: {data.get('error')}")
                break

# Run the client
asyncio.run(generate_image())
```

### JavaScript/Browser Client

```html
<!DOCTYPE html>
<html>
<head>
    <title>ComfyUI Web Client</title>
    <style>
        .progress-bar {
            width: 100%;
            height: 20px;
            background-color: #f0f0f0;
            border-radius: 10px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background-color: #4caf50;
            transition: width 0.3s ease;
        }
        .result-image {
            max-width: 512px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <h1>ComfyUI Generator</h1>

    <div>
        <input type="text" id="prompt" placeholder="Enter your prompt..."
               value="a beautiful landscape painting">
        <button onclick="generateImage()">Generate</button>
    </div>

    <div class="progress-bar">
        <div class="progress-fill" id="progressFill" style="width: 0%"></div>
    </div>
    <div id="status">Ready</div>

    <div id="results"></div>

    <script>
        function generateImage() {
            const prompt = document.getElementById('prompt').value;
            const ws = new WebSocket('wss://your-app.modal.run/api/v1/generate');

            ws.onopen = function() {
                const request = {
                    workflow_id: 'txt2img',
                    params: {
                        'text': prompt,
                        '6.text': prompt,
                        'steps': 20,
                        'cfg': 7.0
                    }
                };
                ws.send(JSON.stringify(request));
                document.getElementById('status').textContent = 'Connecting...';
            };

            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                const status = data.status;

                if (status === 'running' && data.progress) {
                    const percent = (data.progress * 100).toFixed(1);
                    document.getElementById('progressFill').style.width = percent + '%';
                    document.getElementById('status').textContent =
                        `Generating: ${percent}% (${data.current_step}/${data.total_steps})`;
                }
                else if (status === 'result') {
                    const img = document.createElement('img');
                    img.src = 'data:image/png;base64,' + data.result_data;
                    img.className = 'result-image';
                    document.getElementById('results').appendChild(img);
                }
                else if (status === 'completed') {
                    document.getElementById('status').textContent = 'Completed!';
                    document.getElementById('progressFill').style.width = '100%';
                    ws.close();
                }
                else if (status === 'error') {
                    document.getElementById('status').textContent = 'Error: ' + data.error;
                    ws.close();
                }
            };

            ws.onerror = function(error) {
                document.getElementById('status').textContent = 'Connection error';
                console.error('WebSocket error:', error);
            };
        }
    </script>
</body>
</html>
```

### React Component

```jsx
import React, { useState, useCallback } from 'react';

const ComfyUIGenerator = () => {
    const [prompt, setPrompt] = useState('a beautiful landscape painting');
    const [progress, setProgress] = useState(0);
    const [status, setStatus] = useState('Ready');
    const [results, setResults] = useState([]);
    const [isGenerating, setIsGenerating] = useState(false);

    const generateImage = useCallback(async () => {
        if (!prompt.trim()) return;

        setIsGenerating(true);
        setProgress(0);
        setStatus('Connecting...');
        setResults([]);

        try {
            const ws = new WebSocket('wss://your-app.modal.run/api/v1/generate');

            ws.onopen = () => {
                const request = {
                    workflow_id: 'txt2img',
                    params: {
                        'text': prompt,
                        '6.text': prompt,
                        'steps': 25,
                        'cfg': 7.5,
                        'width': 1024,
                        'height': 1024
                    }
                };
                ws.send(JSON.stringify(request));
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);

                switch (data.status) {
                    case 'running':
                        if (data.progress) {
                            setProgress(data.progress * 100);
                            setStatus(`Generating: ${(data.progress * 100).toFixed(1)}% (${data.current_step}/${data.total_steps})`);
                        }
                        if (data.current_node) {
                            setStatus(`Executing: ${data.current_node}`);
                        }
                        break;

                    case 'result':
                        setResults(prev => [...prev, {
                            id: Date.now() + Math.random(),
                            filename: data.filename,
                            data: data.result_data
                        }]);
                        break;

                    case 'completed':
                        setStatus('Completed!');
                        setProgress(100);
                        setIsGenerating(false);
                        ws.close();
                        break;

                    case 'error':
                        setStatus(`Error: ${data.error}`);
                        setIsGenerating(false);
                        ws.close();
                        break;

                    default:
                        setStatus(data.message || data.status);
                }
            };

            ws.onerror = () => {
                setStatus('Connection error');
                setIsGenerating(false);
            };

        } catch (error) {
            setStatus(`Error: ${error.message}`);
            setIsGenerating(false);
        }
    }, [prompt]);

    return (
        <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
            <h1>ComfyUI Image Generator</h1>

            <div style={{ marginBottom: '20px' }}>
                <input
                    type="text"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Enter your prompt..."
                    style={{
                        width: '70%',
                        padding: '10px',
                        marginRight: '10px',
                        fontSize: '16px'
                    }}
                    disabled={isGenerating}
                />
                <button
                    onClick={generateImage}
                    disabled={isGenerating || !prompt.trim()}
                    style={{
                        padding: '10px 20px',
                        fontSize: '16px',
                        backgroundColor: isGenerating ? '#ccc' : '#4caf50',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: isGenerating ? 'not-allowed' : 'pointer'
                    }}
                >
                    {isGenerating ? 'Generating...' : 'Generate'}
                </button>
            </div>

            <div style={{ marginBottom: '20px' }}>
                <div style={{
                    width: '100%',
                    height: '20px',
                    backgroundColor: '#f0f0f0',
                    borderRadius: '10px',
                    overflow: 'hidden'
                }}>
                    <div style={{
                        width: `${progress}%`,
                        height: '100%',
                        backgroundColor: '#4caf50',
                        transition: 'width 0.3s ease'
                    }} />
                </div>
                <div style={{ marginTop: '5px', fontSize: '14px', color: '#666' }}>
                    {status}
                </div>
            </div>

            <div>
                {results.map(result => (
                    <div key={result.id} style={{ marginBottom: '20px' }}>
                        <img
                            src={`data:image/png;base64,${result.data}`}
                            alt={result.filename}
                            style={{ maxWidth: '100%', borderRadius: '8px' }}
                        />
                        <div style={{ fontSize: '12px', color: '#888', marginTop: '5px' }}>
                            {result.filename}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default ComfyUIGenerator;
```

### Node.js Server Integration

```javascript
// server.js - Express.js integration
const express = require('express');
const WebSocket = require('ws');
const app = express();

app.use(express.json());

// Proxy endpoint for ComfyUI generation
app.post('/api/generate', async (req, res) => {
    const { prompt, workflow_id = 'txt2img', ...params } = req.body;

    try {
        // Set up Server-Sent Events for real-time updates
        res.writeHead(200, {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        });

        const ws = new WebSocket('wss://your-app.modal.run/api/v1/generate');

        ws.on('open', () => {
            ws.send(JSON.stringify({
                workflow_id,
                params: {
                    'text': prompt,
                    '6.text': prompt,
                    ...params
                }
            }));
        });

        ws.on('message', (data) => {
            const message = JSON.parse(data);
            res.write(`data: ${JSON.stringify(message)}\n\n`);

            if (message.status === 'completed' || message.status === 'error') {
                ws.close();
                res.end();
            }
        });

        ws.on('error', (error) => {
            res.write(`data: ${JSON.stringify({
                status: 'error',
                error: error.message
            })}\n\n`);
            res.end();
        });

        // Handle client disconnect
        req.on('close', () => {
            ws.close();
        });

    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});
```

### Batch Processing Script

```python
# batch_generator.py - Process multiple prompts
import asyncio
import websockets
import json
import base64
from pathlib import Path
import time

class BatchGenerator:
    def __init__(self, api_url):
        self.api_url = api_url.replace('https://', 'wss://').replace('http://', 'ws://')
        self.results = []

    async def generate_single(self, prompt, workflow_id='txt2img', **params):
        """Generate a single image"""
        uri = f"{self.api_url}/api/v1/generate"

        request = {
            "workflow_id": workflow_id,
            "params": {
                "text": prompt,
                "6.text": prompt,
                **params
            }
        }

        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps(request))

            results = []
            async for message in websocket:
                data = json.loads(message)

                if data.get("status") == "result":
                    # Save image
                    image_data = base64.b64decode(data["result_data"])
                    timestamp = int(time.time())
                    filename = f"batch_{timestamp}_{len(results)}.png"

                    Path("output").mkdir(exist_ok=True)
                    Path(f"output/{filename}").write_bytes(image_data)

                    results.append({
                        "prompt": prompt,
                        "filename": filename,
                        "path": f"output/{filename}"
                    })

                elif data.get("status") == "completed":
                    break
                elif data.get("status") == "error":
                    print(f"Error for prompt '{prompt}': {data.get('error')}")
                    break

            return results

    async def generate_batch(self, prompts, max_concurrent=3, **default_params):
        """Generate multiple images with concurrency control"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_semaphore(prompt):
            async with semaphore:
                return await self.generate_single(prompt, **default_params)

        # Execute all prompts concurrently (limited by semaphore)
        tasks = [generate_with_semaphore(prompt) for prompt in prompts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results and handle exceptions
        all_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Failed to generate for prompt '{prompts[i]}': {result}")
            else:
                all_results.extend(result)

        return all_results

# Usage example
async def main():
    generator = BatchGenerator("https://your-app.modal.run")

    prompts = [
        "a serene mountain landscape at sunrise",
        "a bustling cyberpunk city street at night",
        "a magical forest with glowing mushrooms",
        "a vintage steam locomotive in a desert",
        "an underwater coral reef scene"
    ]

    print(f"Generating {len(prompts)} images...")
    results = await generator.generate_batch(
        prompts,
        max_concurrent=2,  # Limit concurrent requests
        steps=25,
        cfg=7.5,
        width=1024,
        height=1024
    )

    print(f"Generated {len(results)} images successfully:")
    for result in results:
        print(f"  {result['prompt']} -> {result['path']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Docker Deployment Example

```dockerfile
# Dockerfile for client application
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy application code
COPY . .

# Environment variables
ENV COMFYUI_API_URL=https://your-app.modal.run
ENV PORT=3000

# Expose port
EXPOSE 3000

# Start application
CMD ["npm", "start"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  comfyui-client:
    build: .
    ports:
      - "3000:3000"
    environment:
      - COMFYUI_API_URL=https://your-app.modal.run
      - NODE_ENV=production
    volumes:
      - ./output:/app/output
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - comfyui-client
    restart: unless-stopped
```

### CLI Client Tool

```python
#!/usr/bin/env python3
"""
ComfyUI CLI Client - Command line interface for ComfyUI API
Usage: python comfyui_cli.py generate "a beautiful landscape" --workflow txt2img
"""

import asyncio
import argparse
import json
import base64
import websockets
from pathlib import Path
import sys

class ComfyUICLI:
    def __init__(self, api_url):
        self.api_url = api_url.replace('https://', 'wss://').replace('http://', 'ws://')

    async def generate(self, prompt, workflow_id='txt2img', output_dir='output', **params):
        """Generate image via CLI"""
        uri = f"{self.api_url}/api/v1/generate"

        request = {
            "workflow_id": workflow_id,
            "params": {
                "text": prompt,
                "6.text": prompt,
                **params
            }
        }

        print(f"🎨 Generating: {prompt}")
        print(f"📋 Workflow: {workflow_id}")
        print(f"⚙️  Parameters: {params}")
        print("🔗 Connecting to ComfyUI API...")

        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(json.dumps(request))

                async for message in websocket:
                    data = json.loads(message)
                    status = data.get("status")

                    if status == "running":
                        if data.get("progress"):
                            progress = data["progress"] * 100
                            print(f"📊 Progress: {progress:.1f}%", end='\r')
                        if data.get("current_node"):
                            print(f"🔧 Executing: {data['current_node']}")

                    elif status == "result":
                        # Save image
                        image_data = base64.b64decode(data["result_data"])
                        filename = data.get("filename", "generated.png")

                        output_path = Path(output_dir)
                        output_path.mkdir(exist_ok=True)
                        file_path = output_path / filename

                        file_path.write_bytes(image_data)
                        print(f"💾 Saved: {file_path}")

                    elif status == "completed":
                        print("✅ Generation completed!")
                        break

                    elif status == "error":
                        print(f"❌ Error: {data.get('error')}")
                        sys.exit(1)

        except Exception as e:
            print(f"❌ Connection failed: {e}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='ComfyUI CLI Client')
    parser.add_argument('command', choices=['generate'], help='Command to execute')
    parser.add_argument('prompt', help='Text prompt for generation')
    parser.add_argument('--api-url', default='https://your-app.modal.run',
                       help='ComfyUI API URL')
    parser.add_argument('--workflow', default='txt2img',
                       help='Workflow ID to use')
    parser.add_argument('--output', default='output',
                       help='Output directory')
    parser.add_argument('--steps', type=int, default=20,
                       help='Number of sampling steps')
    parser.add_argument('--cfg', type=float, default=7.0,
                       help='CFG scale')
    parser.add_argument('--width', type=int, default=1024,
                       help='Image width')
    parser.add_argument('--height', type=int, default=1024,
                       help='Image height')
    parser.add_argument('--seed', type=int,
                       help='Random seed (optional)')

    args = parser.parse_args()

    if args.command == 'generate':
        params = {
            'steps': args.steps,
            'cfg': args.cfg,
            'width': args.width,
            'height': args.height
        }

        if args.seed:
            params['seed'] = args.seed

        cli = ComfyUICLI(args.api_url)
        asyncio.run(cli.generate(
            args.prompt,
            args.workflow,
            args.output,
            **params
        ))

if __name__ == '__main__':
    main()
```

```bash
# Usage examples:
python comfyui_cli.py generate "a beautiful sunset over mountains"
python comfyui_cli.py generate "cyberpunk city" --workflow txt2img --steps 30 --cfg 8.0
python comfyui_cli.py generate "portrait photo" --width 768 --height 1024 --seed 42
```

## 🎯 Advanced Use Cases

### Image-to-Image Workflows

```json
// img2img.json workflow example
{
  "workflow_id": "img2img",
  "params": {
    "text": "transform this into a painting",
    "input_image": "base64_encoded_image_data",
    "strength": 0.7,  // How much to change the image
    "steps": 25
  }
}
```

### ControlNet Workflows

```json
// controlnet.json workflow example
{
  "workflow_id": "controlnet_canny",
  "params": {
    "text": "a beautiful landscape painting",
    "input_image": "base64_encoded_image_data",
    "control_strength": 1.0,
    "steps": 30
  }
}
```

### Batch API Processing

```python
# For high-volume batch processing
import asyncio
import aiohttp

async def batch_process_rest_api(prompts, api_url):
    """Use REST API for batch processing without WebSocket overhead"""
    async with aiohttp.ClientSession() as session:
        tasks = []

        for prompt in prompts:
            task = session.post(f"{api_url}/api/v1/generate", json={
                "workflow_id": "txt2img",
                "params": {"text": prompt}
            })
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        return [await r.json() for r in responses]
```

### Integration with Cloud Storage

```python
# Upload results directly to cloud storage
{
  "workflow_id": "txt2img",
  "params": {"text": "a beautiful landscape"},
  "output": {
    "bucket": "my-app-outputs",
    "path": "generated/user-123/session-456/",
    "endpoint_url": "https://account.r2.cloudflarestorage.com",
    "access_key_id": "your-key",
    "secret_access_key": "your-secret"
  }
}
```

## 📈 Monitoring and Analytics

### Performance Monitoring

```python
# Add to your client code
import time

class PerformanceMonitor:
    def __init__(self):
        self.metrics = []

    async def monitored_generate(self, prompt, **kwargs):
        start_time = time.time()

        # Your generation code here
        result = await generate_image(prompt, **kwargs)

        duration = time.time() - start_time
        self.metrics.append({
            'prompt': prompt,
            'duration': duration,
            'timestamp': start_time,
            'success': result is not None
        })

        return result

    def get_stats(self):
        if not self.metrics:
            return {}

        durations = [m['duration'] for m in self.metrics]
        success_rate = sum(1 for m in self.metrics if m['success']) / len(self.metrics)

        return {
            'total_requests': len(self.metrics),
            'success_rate': success_rate,
            'avg_duration': sum(durations) / len(durations),
            'min_duration': min(durations),
            'max_duration': max(durations)
        }
```

### Usage Analytics

```python
# Track usage patterns
import json
from datetime import datetime

class UsageAnalytics:
    def __init__(self, log_file='usage.log'):
        self.log_file = log_file

    def log_request(self, user_id, workflow_id, params, duration, success):
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'workflow_id': workflow_id,
            'params': params,
            'duration': duration,
            'success': success
        }

        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def generate_report(self):
        # Analyze usage patterns from logs
        pass
```

## 🔒 Security Best Practices

### Rate Limiting

```python
# Implement rate limiting in your client application
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, max_requests_per_minute=10):
        self.max_requests = max_requests_per_minute
        self.requests = defaultdict(list)

    def can_make_request(self, user_id):
        now = time.time()
        minute_ago = now - 60

        # Clean old requests
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if req_time > minute_ago
        ]

        # Check if under limit
        if len(self.requests[user_id]) < self.max_requests:
            self.requests[user_id].append(now)
            return True

        return False
```

### Input Validation

```python
# Validate user inputs
import re

class InputValidator:
    @staticmethod
    def validate_prompt(prompt):
        if not prompt or len(prompt.strip()) == 0:
            raise ValueError("Prompt cannot be empty")

        if len(prompt) > 1000:
            raise ValueError("Prompt too long (max 1000 characters)")

        # Check for potentially harmful content
        forbidden_patterns = [
            r'\b(nude|nsfw|explicit)\b',
            r'\b(violence|harm|illegal)\b'
        ]

        for pattern in forbidden_patterns:
            if re.search(pattern, prompt.lower()):
                raise ValueError("Inappropriate content detected")

        return prompt.strip()

    @staticmethod
    def validate_workflow_params(params):
        # Validate numeric parameters
        if 'steps' in params:
            if not 1 <= params['steps'] <= 100:
                raise ValueError("Steps must be between 1 and 100")

        if 'cfg' in params:
            if not 1.0 <= params['cfg'] <= 20.0:
                raise ValueError("CFG must be between 1.0 and 20.0")

        return params
```

### Authentication Integration

```python
# Add JWT authentication to your wrapper API
import jwt
from datetime import datetime, timedelta

class AuthManager:
    def __init__(self, secret_key):
        self.secret_key = secret_key

    def generate_token(self, user_id):
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')

    def verify_token(self, token):
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload['user_id']
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
```

---

## 🏁 Conclusion

This ComfyUI Production API provides a complete, scalable solution for deploying ComfyUI workflows in production environments. The combination of Modal's serverless infrastructure, memory snapshots for performance, and WebSocket streaming for real-time updates creates a powerful platform that can handle everything from prototype development to enterprise-scale deployments.

### Key Benefits

- **🚀 Fast**: Memory snapshots reduce cold start time from minutes to seconds
- **💰 Cost-Effective**: Pay only for actual usage with automatic scaling
- **🔧 Developer-Friendly**: Complete CLI tools and clear documentation
- **🏗️ Production-Ready**: Comprehensive error handling and monitoring
- **🔌 Easy Integration**: Multiple client examples and clear APIs
- **📈 Scalable**: Handles traffic spikes automatically

### Next Steps

1. **Deploy your first instance** using the Quick Start guide
2. **Customize workflows** using the development UI
3. **Integrate with your application** using the provided client examples
4. **Monitor and optimize** using the performance tools
5. **Scale to production** with the deployment best practices

For support and updates, refer to the [Modal Documentation](https://modal.com/docs) and the [ComfyUI GitHub repository](https://github.com/comfyanonymous/ComfyUI).

---

*This documentation covers ComfyUI Production API v1.0.0. For the latest updates and features, check the project repository.*
