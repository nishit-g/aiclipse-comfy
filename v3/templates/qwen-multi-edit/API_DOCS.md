# ComfyUI API Documentation

> **Run ANY ComfyUI workflow via API. Authenticated. Fast.**

## 🔐 Authentication (Required)

All API requests require **Modal Proxy Auth** headers:

```bash
curl -H "Modal-Key: YOUR_TOKEN_ID" \
     -H "Modal-Secret: YOUR_TOKEN_SECRET" \
     https://ybshiva--comfy-qwen-multi-edit-serve.modal.run/system_stats
```

**Get your tokens:** [Modal Settings → Proxy Auth Tokens](https://modal.com/settings/proxy-auth-tokens)

---

## 📚 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/prompt` | POST | Queue a workflow |
| `/history/{id}` | GET | Get execution results |
| `/view` | GET | Download images |
| `/ws` | WebSocket | Real-time progress |
| `/upload/image` | POST | Upload input images |
| `/system_stats` | GET | Health check |

---

## 🚀 Quick Start

### Option 1: TypeScript SDK (Recommended)

```bash
npm install @stable-canvas/comfyui-client dotenv
```

```typescript
import { Client } from "@stable-canvas/comfyui-client";
import * as dotenv from "dotenv";
dotenv.config();

// Custom fetch with auth
const authFetch = (url: string | URL | Request, init?: RequestInit) => {
    return fetch(url, {
        ...init,
        headers: {
            ...init?.headers,
            "Modal-Key": process.env.MODAL_TOKEN_ID!,
            "Modal-Secret": process.env.MODAL_TOKEN_SECRET!,
        },
    });
};

const client = new Client({
    api_host: "ybshiva--comfy-qwen-multi-edit-serve.modal.run",
    ssl: true,
    fetch: authFetch as typeof fetch,
});

await client.connect();

// Run workflow and wait for result
const result = await client.enqueue(workflow, {
    progress: ({ max, value }) => console.log(`${value}/${max}`),
});

// Get output image
console.log(result.images[0].data); // URL or Buffer
```

### Option 2: Python (Simple Polling)

```python
import requests
import time

BASE = "https://ybshiva--comfy-qwen-multi-edit-serve.modal.run"
HEADERS = {
    "Modal-Key": "YOUR_TOKEN_ID",
    "Modal-Secret": "YOUR_TOKEN_SECRET",
}

def run_workflow(workflow, timeout=300):
    # 1. Queue the workflow
    r = requests.post(f"{BASE}/prompt", json={"prompt": workflow}, headers=HEADERS)
    prompt_id = r.json()["prompt_id"]
    
    # 2. Poll for completion
    start = time.time()
    while time.time() - start < timeout:
        hist = requests.get(f"{BASE}/history/{prompt_id}", headers=HEADERS).json()
        if prompt_id in hist and hist[prompt_id]["status"].get("completed"):
            return hist[prompt_id]["outputs"]
        time.sleep(2)
    
    raise TimeoutError("Workflow didn't complete")

# Usage
workflow = json.load(open("workflow.json"))
outputs = run_workflow(workflow)

# Download image
for node_id, output in outputs.items():
    for img in output.get("images", []):
        url = f"{BASE}/view?filename={img['filename']}&type={img['type']}"
        r = requests.get(url, headers=HEADERS)
        with open(img['filename'], 'wb') as f:
            f.write(r.content)
```

### Option 3: cURL

```bash
# Health check
curl -H "Modal-Key: $MODAL_TOKEN_ID" \
     -H "Modal-Secret: $MODAL_TOKEN_SECRET" \
     https://ybshiva--comfy-qwen-multi-edit-serve.modal.run/system_stats

# Queue workflow
curl -X POST \
     -H "Modal-Key: $MODAL_TOKEN_ID" \
     -H "Modal-Secret: $MODAL_TOKEN_SECRET" \
     -H "Content-Type: application/json" \
     -d '{"prompt": {...workflow...}}' \
     https://ybshiva--comfy-qwen-multi-edit-serve.modal.run/prompt

# Returns: {"prompt_id": "abc-123", ...}

# Check status
curl -H "Modal-Key: $MODAL_TOKEN_ID" \
     -H "Modal-Secret: $MODAL_TOKEN_SECRET" \
     https://ybshiva--comfy-qwen-multi-edit-serve.modal.run/history/abc-123
```

---

## 📋 Workflow Format

**Important:** You need the workflow in "API Format", not UI format.

### How to Export
1. Open ComfyUI UI → Settings → Enable "Dev mode Options"
2. Load your workflow
3. Click **"Save (API Format)"**

### Example Structure
```json
{
  "65": {
    "inputs": {
      "seed": 12345,
      "steps": 4,
      "model": ["12", 0]
    },
    "class_type": "KSampler"
  },
  "41": {
    "inputs": { "image": "input.png" },
    "class_type": "LoadImage"
  }
}
```

**Common parameters to modify:**
- `seed` - Random number for variation
- `steps` - Quality (higher = slower)
- `image` - Input image filename
- Text prompts in encoder nodes

---

## 📁 Input Images

### Method 1: Pre-upload to Volume (Recommended)
```bash
modal volume put aiclipse-inputs-v2 myimage.png
```
Then use `"image": "myimage.png"` in workflow.

### Method 2: Upload per request
```python
files = {"image": open("myimage.png", "rb")}
r = requests.post(f"{BASE}/upload/image", files=files, headers=HEADERS)
filename = r.json()["name"]
```
⚠️ Ephemeral - lost on container restart.

---

## ⚡ Real-time Progress (WebSocket)

For real-time progress updates:

```python
import websocket
client_id = str(uuid.uuid4())
ws_url = f"wss://ybshiva--comfy-qwen-multi-edit-serve.modal.run/ws?clientId={client_id}"

# Connect with auth headers
ws = websocket.create_connection(
    ws_url,
    header=["Modal-Key: YOUR_TOKEN_ID", "Modal-Secret: YOUR_TOKEN_SECRET"]
)

# Queue with matching client_id
requests.post(f"{BASE}/prompt", json={
    "prompt": workflow,
    "client_id": client_id  # Must match!
}, headers=HEADERS)

# Listen for updates
while True:
    msg = json.loads(ws.recv())
    if msg["type"] == "progress":
        print(f"Step {msg['data']['value']}/{msg['data']['max']}")
    elif msg["type"] == "executing" and msg["data"]["node"] is None:
        print("Done!")
        break
```

---

## 📖 API Reference

### POST /prompt
Queue a workflow.

**Request:**
```json
{
  "prompt": { ...workflow... },
  "client_id": "optional-for-websocket"
}
```

**Response:**
```json
{"prompt_id": "abc-123", "number": 1, "node_errors": {}}
```

### GET /history/{prompt_id}
Get execution results.

**Response:**
```json
{
  "abc-123": {
    "status": {"status_str": "success", "completed": true},
    "outputs": {
      "9": {"images": [{"filename": "result.png", "type": "output"}]}
    }
  }
}
```

### GET /view
Download an image.
```
GET /view?filename=result.png&type=output
```

### POST /upload/image
Upload input image (multipart/form-data).

### GET /system_stats
Health check - returns system info and GPU status.

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| `401 Unauthorized` | Add Modal-Key and Modal-Secret headers |
| `"Image not found"` | Pre-upload to Volume |
| Timeout | Cold start takes 30-60s, retry |
| WebSocket no messages | Match `clientId` in URL and prompt |

---

## 📂 Files

- **API URL:** `https://ybshiva--comfy-qwen-multi-edit-serve.modal.run`
- **Demo scripts:** `v3/templates/qwen-multi-edit/demo/src/`
- **Workflows:** `v3/templates/qwen-multi-edit/workflows/`
