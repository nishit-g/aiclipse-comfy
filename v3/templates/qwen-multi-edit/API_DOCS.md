# Qwen Multi-Edit API Documentation

> **Production API for Qwen-Image-Edit-2511 with Lightning acceleration**

## Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/prompt` | POST | Queue a workflow for execution |
| `/ws` | WebSocket | Real-time execution progress & results |
| `/history/{prompt_id}` | GET | Retrieve execution results |
| `/view` | GET | Download generated images |
| `/upload/image` | POST | Upload input images |
| `/system_stats` | GET | Health check & system info |

---

## Base URL

```
Production: https://ybshiva--comfy-qwen-multi-edit-serve.modal.run
```

---

## Authentication

Currently **no authentication required**. For production, consider enabling [Modal Proxy Auth Tokens](https://modal.com/docs/guide/proxy-auth-tokens).

---

## API Endpoints

### 1. Queue Workflow (`POST /prompt`)

Queue a ComfyUI workflow for execution.

**Request:**

```bash
curl -X POST "https://ybshiva--comfy-qwen-multi-edit-serve.modal.run/prompt" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": { /* workflow JSON */ },
    "client_id": "my-client-id"
  }'
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | object | ✅ | ComfyUI workflow in API format |
| `client_id` | string | ❌ | Optional client identifier for WebSocket |

**Response (Success - 200):**

```json
{
  "prompt_id": "abc123-def456-...",
  "number": 1,
  "node_errors": {}
}
```

**Response (Validation Error):**

```json
{
  "error": "Validation error message",
  "node_errors": {
    "12": {
      "class_type": "LoadImage",
      "input_name": "image",
      "error": "File not found: missing.png"
    }
  }
}
```

---

### 2. WebSocket Connection (`/ws`)

Connect to receive real-time execution updates.

**Connection:**

```javascript
const ws = new WebSocket("wss://ybshiva--comfy-qwen-multi-edit-serve.modal.run/ws");

ws.onmessage = (event) => {
  if (typeof event.data === "string") {
    const data = JSON.parse(event.data);
    console.log(data.type, data.data);
  } else {
    // Binary data (image from SaveImageWebsocket)
    const imageBlob = event.data.slice(8); // Skip 8-byte header
  }
};
```

**Message Types:**

| Type | Description | Data |
|------|-------------|------|
| `status` | Queue status | `{ "exec_info": { "queue_remaining": n } }` |
| `executing` | Node started | `{ "node": "65", "prompt_id": "..." }` |
| `progress` | Step progress | `{ "value": 3, "max": 4, "prompt_id": "..." }` |
| `execution_complete` | Finished | `{ "prompt_id": "..." }` |
| `execution_error` | Error | `{ "prompt_id": "...", "exception_message": "..." }` |
| (binary) | Image data | Raw PNG with 8-byte header |

---

### 3. Get Execution History (`GET /history/{prompt_id}`)

Retrieve results after execution completes.

**Request:**

```bash
curl "https://ybshiva--comfy-qwen-multi-edit-serve.modal.run/history/abc123-def456"
```

**Response:**

```json
{
  "abc123-def456": {
    "prompt": [ /* original workflow */ ],
    "outputs": {
      "9": {
        "images": [
          {
            "filename": "api_test_00001_.png",
            "subfolder": "",
            "type": "output"
          }
        ]
      }
    },
    "status": {
      "status_str": "success",
      "completed": true,
      "messages": [...]
    }
  }
}
```

---

### 4. Download Image (`GET /view`)

Download generated or input images.

**Request:**

```bash
curl "https://ybshiva--comfy-qwen-multi-edit-serve.modal.run/view?filename=api_test_00001_.png&subfolder=&type=output" \
  --output result.png
```

**Query Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `filename` | ✅ | Image filename |
| `subfolder` | ❌ | Subfolder path (default: "") |
| `type` | ✅ | `input`, `output`, or `temp` |

---

### 5. Upload Image (`POST /upload/image`)

Upload input images for workflows.

**Request:**

```bash
curl -X POST "https://ybshiva--comfy-qwen-multi-edit-serve.modal.run/upload/image" \
  -F "image=@/path/to/image.png" \
  -F "overwrite=true"
```

**Response:**

```json
{
  "name": "image.png",
  "subfolder": "",
  "type": "input"
}
```

> **Note:** For persistent input images across containers, use Modal Volume:
> ```bash
> modal volume put aiclipse-inputs-v2 myimage.png
> ```

---

### 6. Health Check (`GET /system_stats`)

Check server status and GPU info.

**Request:**

```bash
curl "https://ybshiva--comfy-qwen-multi-edit-serve.modal.run/system_stats"
```

**Response:**

```json
{
  "devices": [
    {
      "name": "cuda:0 NVIDIA A10G",
      "vram_total": 24576,
      "vram_free": 18432
    }
  ]
}
```

---

## Complete Usage Examples

### Python Example (Full Flow)

```python
#!/usr/bin/env python3
"""Complete example: Queue workflow, monitor via WebSocket, download result."""

import json
import time
import requests
import websocket

BASE_URL = "https://ybshiva--comfy-qwen-multi-edit-serve.modal.run"

# 1. Load workflow (use API format from ComfyUI)
workflow = json.load(open("workflow.json"))

# 2. Optionally modify workflow parameters
workflow["65"]["inputs"]["seed"] = int(time.time())  # Random seed

# 3. Connect WebSocket for real-time updates
ws = websocket.create_connection(f"{BASE_URL.replace('https', 'wss')}/ws")

# 4. Queue the workflow
response = requests.post(
    f"{BASE_URL}/prompt",
    json={"prompt": workflow, "client_id": "python-client"}
)
result = response.json()
prompt_id = result["prompt_id"]
print(f"Queued: {prompt_id}")

# 5. Wait for completion via WebSocket
while True:
    msg = ws.recv()
    if isinstance(msg, bytes):
        # Image received via SaveImageWebsocket node
        with open("output.png", "wb") as f:
            f.write(msg[8:])  # Skip 8-byte header
        print("Saved: output.png")
        break
    else:
        data = json.loads(msg)
        if data["type"] == "progress":
            print(f"Progress: {data['data']['value']}/{data['data']['max']}")
        elif data["type"] == "execution_complete":
            break

ws.close()

# 6. Get results from history
history = requests.get(f"{BASE_URL}/history/{prompt_id}").json()
outputs = history[prompt_id]["outputs"]

# 7. Download images
for node_id, node_output in outputs.items():
    if "images" in node_output:
        for img in node_output["images"]:
            img_url = f"{BASE_URL}/view?filename={img['filename']}&type={img['type']}"
            img_data = requests.get(img_url).content
            with open(img["filename"], "wb") as f:
                f.write(img_data)
            print(f"Downloaded: {img['filename']}")
```

### JavaScript/Node.js Example

```javascript
const WebSocket = require('ws');
const fs = require('fs');

const BASE_URL = 'https://ybshiva--comfy-qwen-multi-edit-serve.modal.run';

async function runWorkflow(workflow) {
  // Connect WebSocket
  const ws = new WebSocket(`${BASE_URL.replace('https', 'wss')}/ws`);
  
  return new Promise((resolve, reject) => {
    ws.on('open', async () => {
      // Queue workflow
      const response = await fetch(`${BASE_URL}/prompt`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: workflow })
      });
      
      const { prompt_id } = await response.json();
      console.log('Queued:', prompt_id);
    });
    
    ws.on('message', (data) => {
      if (Buffer.isBuffer(data)) {
        // Binary image data
        fs.writeFileSync('output.png', data.slice(8));
        ws.close();
        resolve('output.png');
      } else {
        const msg = JSON.parse(data.toString());
        if (msg.type === 'progress') {
          console.log(`Progress: ${msg.data.value}/${msg.data.max}`);
        }
      }
    });
    
    ws.on('error', reject);
  });
}

// Usage
const workflow = require('./workflow.json');
runWorkflow(workflow).then(console.log);
```

---

## Workflow Format

Workflows must be in **ComfyUI API format** (not the standard UI format).

**Exporting from ComfyUI UI:**
1. Enable "Dev Mode" in ComfyUI settings
2. Click "Save (API format)" button
3. Use the exported JSON with this API

**Example Workflow Structure:**

```json
{
  "8": {
    "inputs": {
      "samples": ["65", 0],
      "vae": ["10", 0]
    },
    "class_type": "VAEDecode",
    "_meta": { "title": "VAE Decode" }
  },
  "9": {
    "inputs": {
      "filename_prefix": "api_test",
      "images": ["8", 0]
    },
    "class_type": "SaveImage"
  }
}
```

**Key Points:**
- Node IDs are string keys (e.g., `"8"`, `"9"`)
- Connections use `[node_id, output_index]` format
- `class_type` specifies the node type
- `inputs` contains all node parameters

---

## Available Models

The deployed template includes:

| Model | Type | Size |
|-------|------|------|
| `qwen_image_edit_2511_bf16.safetensors` | Diffusion Model | ~38 GB |
| `qwen_2.5_vl_7b_fp8_scaled.safetensors` | Text Encoder | ~8.7 GB |
| `qwen_image_vae.safetensors` | VAE | ~242 MB |
| `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` | LoRA (4-step) | ~1 GB |
| `Qwen-Image-Lightning-8steps-V2.0-bf16.safetensors` | LoRA (8-step) | ~1 GB |
| `v2_hk_000014000.safetensors` | Custom LoRA | ~1 GB |

---

## Input Images

**Option 1: Upload via API (ephemeral)**
```bash
curl -X POST "$BASE_URL/upload/image" -F "image=@input.png"
```
> ⚠️ Images uploaded via API are **per-container** and may not persist across restarts.

**Option 2: Modal Volume (persistent, recommended)**
```bash
modal volume put aiclipse-inputs-v2 input.png
```
Then reference as `input.png` in LoadImage nodes.

---

## Test Script

A ready-to-use test script is available:

```bash
# Run with default workflow
python v3/templates/qwen-multi-edit/test_api.py

# Custom workflow
python v3/templates/qwen-multi-edit/test_api.py --workflow path/to/workflow.json

# Different server
python v3/templates/qwen-multi-edit/test_api.py --base-url https://your-server.modal.run
```

---

## Error Handling

| HTTP Code | Meaning | Action |
|-----------|---------|--------|
| 200 | Success | Process response |
| 400 | Validation error | Check `node_errors` for details |
| 500 | Server error | Retry or check logs |
| 503 | Container starting | Wait and retry (cold start) |

**Common Errors:**

1. **File not found** - Input image doesn't exist
   ```json
   {"node_errors": {"41": {"error": "Image not found: missing.png"}}}
   ```
   → Upload image or use Modal Volume

2. **Missing model** - Model file not downloaded
   ```bash
   modal run v3/templates/qwen-multi-edit/modal/app.py::download_models
   ```

3. **CUDA OOM** - GPU out of memory
   → Reduce image size or wait for container restart

---

## Performance Tips

1. **Use WebSocket** - Avoid polling `/history`, use `/ws` for real-time updates
2. **Batch requests** - Queue multiple workflows without waiting
3. **Persistent inputs** - Use Modal Volume for frequently-used input images
4. **Randomize seeds** - Set unique seeds to prevent caching issues

---

## Related Resources

- [ComfyUI API Docs](https://docs.comfy.org/essentials/comfyui_as_api)
- [Modal Deployment Docs](https://modal.com/docs/guide/web-endpoints)
- [Project README](../../../README.md)
- [Architecture Overview](../../../ARCHITECTURE.md)
