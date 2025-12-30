# ComfyUI API Documentation

> **Run ANY ComfyUI workflow via API. Fast.**

## API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/run` | POST | **Simple API** - Queue workflow, optionally wait for result |
| `/status` | GET | Check run status |
| `/prompt` | POST | Raw ComfyUI - Queue workflow |
| `/ws` | WebSocket | Real-time progress |
| `/history/{id}` | GET | Raw ComfyUI - Get results |
| `/view` | GET | Download images |

---

## TL;DR - 30 Second Quickstart

### Python

```python
import requests

BASE = "https://ybshiva--comfy-qwen-multi-edit-run.modal.run"
workflow = {"65": {...}, "41": {...}}  # Your workflow JSON

# One-liner: wait=true returns result directly
r = requests.post(BASE, json={"workflow": workflow, "wait": True})
result = r.json()

# Get image URL
if result["status"] == "completed":
    print(result["outputs"][0]["url"])  # /view?filename=...
```

### TypeScript / JavaScript (Recommended)

We recommend using the **[@stable-canvas/comfyui-client](https://github.com/StableCanvas/comfyui-client)** library. It handles WebSocket connections, type safety, and queue management for you.

**Installation:**
```bash
npm install @stable-canvas/comfyui-client
```

**Usage:**

```typescript
import { Client } from "@stable-canvas/comfyui-client";

// Connect to the API
const client = new Client({
  api_host: "ybshiva--comfy-qwen-multi-edit-serve.modal.run",
  ssl: true, // Use SSL for Modal URLs
});

await client.connect();

// Run workflow & wait for result
const result = await client.enqueue(workflow, {
  progress: ({ max, value }) => {
    console.log(`Progress: ${Math.round((value / max) * 100)}%`);
  },
});

// Get output image
const img = result.images[0];
console.log("Output:", img.data); // URL or Buffer
```

### cURL

```bash
# Sync mode (wait for result)
curl -X POST "https://ybshiva--comfy-qwen-multi-edit-run.modal.run" \
  -H "Content-Type: application/json" \
  -d '{"workflow": {...}, "wait": true}'

# Async mode (returns immediately)
curl -X POST "https://ybshiva--comfy-qwen-multi-edit-run.modal.run" \
  -H "Content-Type: application/json" \
  -d '{"workflow": {...}}'
# Returns: {"run_id": "abc-123", "status": "queued"}

# Check status
curl "https://ybshiva--comfy-qwen-multi-edit-status.modal.run?run_id=abc-123"
```

---

## Simple API Reference

### POST /run

Queue a workflow. Use `wait: true` to get result synchronously.

**Request:**
```json
{
  "workflow": { ... },      // Required: ComfyUI workflow JSON
  "wait": true,             // Optional: Block until done (default: false)
  "timeout": 300,           // Optional: Max wait seconds (default: 300)
  "webhook_url": "https://..." // Optional: POST result here when done
}
```

**Response:**
```json
{
  "run_id": "abc-123-def",
  "status": "completed",    // queued | processing | completed | failed
  "outputs": [
    {
      "node_id": "9",
      "filename": "result_00001_.png",
      "url": "/view?filename=result_00001_.png&type=output",
      "type": "output"
    }
  ],
  "error": null
}
```

### GET /status

Check status of a run.

```
GET /status?run_id=abc-123-def
```

Same response format as `/run`.

---


## Step 1: Get Your Workflow in API Format

**This is the most important step.** You need the workflow in "API format", not the default UI format.

### How to Export API Format

1. Open ComfyUI web UI
2. Go to **Settings** → Enable **"Dev mode Options"**
3. Load/create your workflow
4. Click **"Save (API Format)"** button
5. Save the JSON file

### Difference

| UI Format | API Format |
|-----------|------------|
| Contains visual layout, positions | Just nodes and connections |
| 1000+ lines | 100-300 lines |
| Not usable with API | ✅ Required for API |

---

## Step 2: Understand the Workflow JSON

Your workflow JSON looks like this:

```json
{
  "65": {
    "inputs": {
      "seed": 12345,           // ← Parameters you can change
      "steps": 4,
      "model": ["12", 0]       // ← Connection: node 12, output 0
    },
    "class_type": "KSampler"
  },
  "41": {
    "inputs": {
      "image": "input.png"     // ← Input image filename
    },
    "class_type": "LoadImage"
  }
}
```

**Key things to modify:**
- `seed` - Random number for variation
- `steps` - Quality (more = better but slower)
- `image` - Input image filename (must exist on server)
- Any `prompt` fields in text encoders

---

## Step 3: Upload Input Images

**Option A: Pre-upload to Volume (Recommended)**
```bash
# Upload once, use forever
modal volume put aiclipse-inputs-v2 myimage.png
```
Then use `"image": "myimage.png"` in your workflow.

**Option B: Upload per-request**
```python
files = {"image": open("myimage.png", "rb")}
r = requests.post(f"{BASE}/upload/image", files=files)
filename = r.json()["name"]  # Use this in workflow
```
⚠️ Per-request uploads are ephemeral (lost on container restart).

---

## Step 4: Modify Workflow Parameters

```python
import json
import random

workflow = json.load(open("workflow.json"))

# Change seed for different results
workflow["65"]["inputs"]["seed"] = random.randint(1, 999999999)

# Change input image
workflow["41"]["inputs"]["image"] = "my_uploaded_image.png"

# Change prompt (find the text encoder node)
workflow["68"]["inputs"]["prompt"] = "Make it blue"
```

**Find the right node IDs by:**
1. Looking at `"class_type"` values in the JSON
2. Or checking `"_meta": {"title": "..."}` if present

---

## Step 5: Queue and Wait

### Method A: Simple Polling (Easiest)

```python
import requests
import time

def run_workflow(workflow, base_url, timeout=300):
    # Queue
    r = requests.post(f"{base_url}/prompt", json={"prompt": workflow})
    result = r.json()
    
    if "node_errors" in result and result["node_errors"]:
        raise Exception(f"Workflow errors: {result['node_errors']}")
    
    prompt_id = result["prompt_id"]
    
    # Poll until done
    start = time.time()
    while time.time() - start < timeout:
        hist = requests.get(f"{base_url}/history/{prompt_id}").json()
        if prompt_id in hist:
            status = hist[prompt_id].get("status", {})
            if status.get("completed"):
                return hist[prompt_id]["outputs"]
        time.sleep(2)
    
    raise TimeoutError("Workflow didn't complete in time")
```

### Method B: WebSocket (Real-time Progress)

```python
import websocket
import uuid

client_id = str(uuid.uuid4())
ws_url = f"wss://...modal.run/ws?clientId={client_id}"

ws = websocket.create_connection(ws_url)

# Queue with matching client_id
requests.post(f"{BASE}/prompt", json={
    "prompt": workflow,
    "client_id": client_id  # MUST match WebSocket clientId
})

# Listen for events
while True:
    msg = json.loads(ws.recv())
    if msg["type"] == "progress":
        print(f"Step {msg['data']['value']}/{msg['data']['max']}")
    elif msg["type"] == "executing" and msg["data"]["node"] is None:
        print("Done!")
        break
```

---

## Step 6: Download Results

```python
# After workflow completes, outputs look like:
outputs = {
    "9": {  # Node ID of SaveImage
        "images": [
            {"filename": "result_00001_.png", "subfolder": "", "type": "output"}
        ]
    }
}

# Download each image
for node_id, node_output in outputs.items():
    for img in node_output.get("images", []):
        url = f"{BASE}/view?filename={img['filename']}&type={img['type']}"
        r = requests.get(url)
        with open(img['filename'], 'wb') as f:
            f.write(r.content)
```

---

## API Reference

### POST /prompt

Queue a workflow.

```
POST /prompt
Content-Type: application/json

{
  "prompt": { ... workflow JSON ... },
  "client_id": "optional-for-websocket"
}
```

**Response:**
```json
{"prompt_id": "abc-123", "number": 1, "node_errors": {}}
```

---

### GET /history/{prompt_id}

Get execution result.

```
GET /history/abc-123
```

**Response:**
```json
{
  "abc-123": {
    "status": {"status_str": "success", "completed": true},
    "outputs": {
      "9": {"images": [{"filename": "...", "type": "output"}]}
    }
  }
}
```

---

### GET /view

Download an image.

```
GET /view?filename=result.png&type=output&subfolder=
```

**Response:** Image bytes (PNG/JPEG)

---

### POST /upload/image

Upload an input image.

```
POST /upload/image
Content-Type: multipart/form-data

image: <file>
overwrite: true
```

**Response:**
```json
{"name": "image.png", "subfolder": "", "type": "input"}
```

---

### GET /system_stats

Health check.

```
GET /system_stats
```

**Response:**
```json
{
  "system": {"comfyui_version": "0.6.0"},
  "devices": [{"name": "cuda:0 NVIDIA A10G"}]
}
```

---

### WebSocket /ws

Real-time updates. **Connect with clientId query param.**

```
wss://...modal.run/ws?clientId=your-uuid
```

**Message types:**
| Type | Meaning |
|------|---------|
| `progress` | Step progress: `{value: 3, max: 4}` |
| `executing` | Node running: `{node: "65"}` |
| `executing` + `node: null` | **Done** |
| `execution_error` | Error occurred |
| **(binary)** | Image from SaveImageWebsocket |

---

## Output Nodes: SaveImage vs SaveImageWebsocket

Your workflow can use different nodes to output images:

### SaveImage (Default)

- Saves to disk on server
- You fetch via `/history` → `/view`
- **Use when:** You need persistent outputs, multiple images

```json
{
  "9": {
    "inputs": {
      "filename_prefix": "result",
      "images": ["8", 0]
    },
    "class_type": "SaveImage"
  }
}
```

**To get results:**
```python
# 1. Wait for completion
# 2. GET /history/{prompt_id}
# 3. GET /view?filename=...
```

### SaveImageWebsocket (Faster)

- Sends image directly via WebSocket as binary
- No disk I/O, faster
- **Use when:** You want real-time results, single image output

```json
{
  "9": {
    "inputs": {
      "images": ["8", 0]
    },
    "class_type": "SaveImageWebsocket"
  }
}
```

**To get results:**
```python
# Binary data arrives via WebSocket automatically
```

---

## Complete WebSocket Example with SaveImageWebsocket

This is the **fastest way** to get results - images stream directly to you.

```python
import websocket
import requests
import json
import uuid

BASE = "https://ybshiva--comfy-qwen-multi-edit-serve.modal.run"

def run_workflow_websocket(workflow, timeout=300):
    """Run workflow and receive image via WebSocket (fastest method)."""
    
    # 1. Generate unique client ID
    client_id = str(uuid.uuid4())
    ws_url = BASE.replace("https://", "wss://") + f"/ws?clientId={client_id}"
    
    # 2. Connect WebSocket
    ws = websocket.create_connection(ws_url, timeout=30)
    
    # 3. Queue workflow (client_id MUST match)
    r = requests.post(f"{BASE}/prompt", json={
        "prompt": workflow,
        "client_id": client_id
    })
    result = r.json()
    
    if result.get("node_errors"):
        ws.close()
        raise Exception(f"Workflow errors: {result['node_errors']}")
    
    prompt_id = result["prompt_id"]
    print(f"Queued: {prompt_id}")
    
    # 4. Listen for messages
    images = []
    
    while True:
        ws.settimeout(5.0)
        try:
            msg = ws.recv()
        except websocket.WebSocketTimeoutException:
            continue
        
        # Binary = image from SaveImageWebsocket
        if isinstance(msg, bytes):
            # Format: 4 bytes type + 4 bytes format + image data
            image_data = msg[8:]  # Skip 8-byte header
            images.append(image_data)
            print(f"Received image: {len(image_data):,} bytes")
        
        # JSON = status message
        else:
            data = json.loads(msg)
            msg_type = data.get("type")
            
            if msg_type == "progress":
                p = data["data"]
                print(f"Progress: {p['value']}/{p['max']}")
            
            elif msg_type == "executing":
                node = data["data"].get("node")
                exec_prompt = data["data"].get("prompt_id")
                
                # node=None means execution finished
                if node is None and exec_prompt == prompt_id:
                    print("Execution complete!")
                    break
            
            elif msg_type == "execution_error":
                ws.close()
                raise Exception(f"Execution error: {data['data']}")
    
    ws.close()
    return images

# Usage
workflow = json.load(open("workflow_with_saveimagewebsocket.json"))
images = run_workflow_websocket(workflow)

# Save the images
for i, img_data in enumerate(images):
    with open(f"output_{i}.png", "wb") as f:
        f.write(img_data)
    print(f"Saved output_{i}.png")
```

### Binary Format Details

When using `SaveImageWebsocket`, binary messages have this format:

```
┌────────────┬────────────┬─────────────────────┐
│ Type (4B)  │ Format (4B)│ Image Data (PNG)    │
│ 0x00000001 │ 0x00000002 │ ...PNG bytes...     │
└────────────┴────────────┴─────────────────────┘
```

Just skip the first 8 bytes: `image_data = msg[8:]`

---

## Getting ALL Outputs (Multiple SaveImage Nodes)

If your workflow has multiple output nodes:

```python
def get_all_outputs(prompt_id, base_url):
    """Get all images from all output nodes."""
    
    hist = requests.get(f"{base_url}/history/{prompt_id}").json()
    
    if prompt_id not in hist:
        return []
    
    all_images = []
    outputs = hist[prompt_id].get("outputs", {})
    
    for node_id, node_output in outputs.items():
        # Images from SaveImage nodes
        if "images" in node_output:
            for img in node_output["images"]:
                img_info = {
                    "node_id": node_id,
                    "filename": img["filename"],
                    "type": img["type"],
                    "subfolder": img.get("subfolder", ""),
                }
                
                # Download the image
                url = f"{base_url}/view?filename={img['filename']}&type={img['type']}&subfolder={img.get('subfolder', '')}"
                r = requests.get(url)
                img_info["data"] = r.content
                img_info["size"] = len(r.content)
                
                all_images.append(img_info)
    
    return all_images

# Usage
images = get_all_outputs("abc-123", BASE)

for img in images:
    print(f"Node {img['node_id']}: {img['filename']} ({img['size']:,} bytes)")
    with open(img['filename'], 'wb') as f:
        f.write(img['data'])
```

### Output Structure Example

```json
{
  "abc-123": {
    "outputs": {
      "9": {
        "images": [
          {"filename": "result_00001_.png", "type": "output", "subfolder": ""}
        ]
      },
      "15": {
        "images": [
          {"filename": "preview_00001_.png", "type": "output", "subfolder": "previews"}
        ]
      }
    }
  }
}
```

## Common Patterns

### Run Same Workflow with Different Inputs

```python
def generate_variation(source_image: str, prompt: str, seed: int = None):
    workflow = json.load(open("template.json"))
    
    # Modify
    workflow["41"]["inputs"]["image"] = source_image
    workflow["68"]["inputs"]["prompt"] = prompt
    workflow["65"]["inputs"]["seed"] = seed or random.randint(1, 999999999)
    
    # Run
    return run_workflow(workflow, BASE)
```

### Batch Process Multiple Images

```python
from concurrent.futures import ThreadPoolExecutor

images = ["img1.png", "img2.png", "img3.png"]

with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(
        lambda img: generate_variation(img, "enhance quality"),
        images
    ))
```

### Error Handling

```python
r = requests.post(f"{BASE}/prompt", json={"prompt": workflow})
result = r.json()

if r.status_code != 200:
    print(f"HTTP Error: {r.status_code}")
    
if result.get("node_errors"):
    for node_id, error in result["node_errors"].items():
        print(f"Node {node_id} ({error.get('class_type')}): {error}")
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `"Image not found"` | Input image doesn't exist | Upload via Volume or /upload/image |
| WebSocket no messages | clientId mismatch | Use same clientId in URL and prompt |
| Timeout | Cold start or slow workflow | Increase timeout, wait 60-90s |
| `500 error` | Model not loaded | Run `modal run app.py::download_models` |

---

## Performance Tips

1. **Pre-upload inputs** to Modal Volume (not per-request)
2. **Keep container warm** - First request takes 60-90s (cold start)
3. **Use polling for simple cases** - WebSocket adds complexity
4. **Batch when possible** - Queue multiple workflows in parallel

---

## Files

- **Production URL:** `https://ybshiva--comfy-qwen-multi-edit-serve.modal.run`
- **Test script:** `v3/templates/qwen-multi-edit/test_api.py`
- **Workflows:** `v3/templates/qwen-multi-edit/workflows/`
