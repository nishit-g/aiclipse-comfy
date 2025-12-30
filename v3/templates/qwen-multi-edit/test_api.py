#!/usr/bin/env python3
"""
ComfyUI API Test Script

Tests the native ComfyUI API with WebSocket for real-time results.

Usage:
    python test_api.py                 # Run with default workflow
    python test_api.py --workflow path/to/workflow.json
    python test_api.py --base-url https://your-server.modal.run
"""

import argparse
import json
import sys
import time
from pathlib import Path

try:
    import requests
    import websocket
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "requests", "websocket-client", "-q"], check=True)
    import requests
    import websocket

# Default configuration
DEFAULT_BASE_URL = "https://ybshiva--comfy-qwen-multi-edit-serve.modal.run"
DEFAULT_WORKFLOW = Path(__file__).parent / "workflows/test-2511-api.json"


def print_progress_bar(value: int, max_val: int, width: int = 40):
    """Print a progress bar."""
    pct = value / max_val if max_val > 0 else 0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    print(f"\r   [{bar}] {value}/{max_val} ({pct*100:.0f}%)", end="", flush=True)


def _fetch_and_download_outputs(base_url: str, prompt_id: str, output_file: Path) -> bool:
    """Fetch outputs from history and download images."""
    print("   Fetching outputs from /history...")
    try:
        hist = requests.get(f"{base_url}/history/{prompt_id}", timeout=10)
        if hist.status_code == 200:
            hist_data = hist.json()
            if prompt_id in hist_data:
                outputs = hist_data[prompt_id].get("outputs", {})
                if outputs:
                    for node_id, node_output in outputs.items():
                        if "images" in node_output:
                            for img in node_output["images"]:
                                filename = img.get("filename")
                                subfolder = img.get("subfolder", "")
                                img_type = img.get("type", "output")
                                print(f"   📸 Found: {filename}")
                                
                                view_url = f"{base_url}/view?filename={filename}&subfolder={subfolder}&type={img_type}"
                                img_resp = requests.get(view_url, timeout=30)
                                if img_resp.status_code == 200:
                                    output_file.write_bytes(img_resp.content)
                                    print(f"   ✅ Saved: {output_file} ({len(img_resp.content):,} bytes)")
                                    return True
                                else:
                                    print(f"   ❌ Failed to download: {img_resp.status_code}")
                else:
                    print("   No outputs in history")
    except Exception as e:
        print(f"   Could not fetch history: {e}")
    return False


def test_comfy_api(base_url: str, workflow_path: Path, timeout: int = 600) -> bool:
    """
    Test ComfyUI API by queueing a workflow and listening for results via WebSocket.
    
    Args:
        base_url: ComfyUI server URL
        workflow_path: Path to workflow JSON file
        timeout: Maximum time to wait for results (seconds)
        
    Returns:
        True if successful, False otherwise
    """
    # Generate unique client_id for this session
    import uuid
    client_id = str(uuid.uuid4())
    
    # IMPORTANT: client_id must be in WebSocket URL query param AND prompt payload
    # Otherwise ComfyUI won't route execution messages to this connection
    ws_url = base_url.replace("https://", "wss://").replace("http://", "ws://") + f"/ws?clientId={client_id}"
    
    # Load workflow
    if not workflow_path.exists():
        print(f"❌ Workflow not found: {workflow_path}")
        return False
        
    workflow = json.loads(workflow_path.read_text())
    print(f"📋 Loaded workflow: {workflow_path.name}")
    print(f"   Nodes: {len(workflow)}")
    
    # Randomize seed to prevent caching
    import random
    new_seed = random.randint(1, 999999999999)
    for node_id, node in workflow.items():
        if node.get("class_type") == "KSampler":
            node["inputs"]["seed"] = new_seed
            print(f"   🎲 Randomized seed: {new_seed} (node {node_id})")
    
    # Show key nodes
    for node_id, node in workflow.items():
        class_type = node.get("class_type", "Unknown")
        if class_type in ["LoadImage", "SaveImage", "SaveImageWebsocket", "KSampler"]:
            print(f"   - [{node_id}] {class_type}")
    
    # Connect to WebSocket
    print(f"\n🔌 Connecting to WebSocket...")
    try:
        ws = websocket.create_connection(ws_url, timeout=30)
        print("✅ WebSocket connected!")
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return False
    
    # Queue prompt
    print(f"\n🚀 Queueing workflow via /prompt...")
    try:
        response = requests.post(
            f"{base_url}/prompt",
            json={"prompt": workflow, "client_id": client_id},
            timeout=60
        )
    except Exception as e:
        print(f"❌ Request failed: {e}")
        ws.close()
        return False
    
    if response.status_code != 200:
        print(f"❌ Error {response.status_code}: {response.text[:200]}")
        ws.close()
        return False
    
    result = response.json()
    prompt_id = result.get("prompt_id")
    node_errors = result.get("node_errors", {})
    
    if node_errors:
        print(f"⚠️  Node errors: {json.dumps(node_errors, indent=2)}")
        ws.close()
        return False
    
    print(f"✅ Queued! Prompt ID: {prompt_id}")
    
    # Listen for results
    print(f"\n📡 Listening for execution...")
    start_time = time.time()
    output_file = workflow_path.parent / f"output_{int(time.time())}.png"
    current_node = None
    success = False
    
    # Track execution
    executed_nodes = []
    
    while time.time() - start_time < timeout:
        try:
            ws.settimeout(5.0)  # 5 second timeout per message
            msg = ws.recv()
            
            # Check if binary (image from SaveImageWebsocket)
            if isinstance(msg, bytes):
                # Skip 8-byte header (4 bytes type + 4 bytes format)
                image_data = msg[8:]
                output_file.write_bytes(image_data)
                print(f"\n\n📸 Received image: {len(image_data):,} bytes")
                print(f"✅ Saved to: {output_file}")
                success = True
                break
            else:
                data = json.loads(msg)
                msg_type = data.get("type")
                msg_data = data.get("data", {})
                
                if msg_type == "progress":
                    value = msg_data.get("value", 0)
                    max_val = msg_data.get("max", 1)
                    print_progress_bar(value, max_val)
                    
                elif msg_type == "executing":
                    node = msg_data.get("node")
                    exec_prompt_id = msg_data.get("prompt_id")
                    if node and node != current_node:
                        current_node = node
                        node_class = workflow.get(node, {}).get("class_type", "?")
                        print(f"\n   🔄 Node [{node}] {node_class}")
                        executed_nodes.append(node)
                    elif node is None and exec_prompt_id == prompt_id:
                        # Execution finished for this prompt (node: null means done)
                        print(f"\n\n✅ Execution complete!")
                        success = _fetch_and_download_outputs(base_url, prompt_id, output_file)
                        break
                        
                elif msg_type in ["execution_complete", "execution_success"]:
                    print(f"\n\n✅ Execution complete!")
                    success = _fetch_and_download_outputs(base_url, prompt_id, output_file)
                    break
                    
                elif msg_type == "execution_error":
                    print(f"\n❌ Execution error: {msg_data}")
                    break
                    
                elif msg_type == "status":
                    # Queue status, ignore
                    pass
                    
        except websocket.WebSocketTimeoutException:
            # No message in 5 seconds, continue waiting
            continue
        except Exception as e:
            print(f"\n❌ Error receiving message: {e}")
            break
    
    elapsed = time.time() - start_time
    print(f"\n⏱️  Total time: {elapsed:.1f}s")
    print(f"   Nodes executed: {len(executed_nodes)}")
    
    ws.close()
    return success


def main():
    parser = argparse.ArgumentParser(description="Test ComfyUI API")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Server URL")
    parser.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW, help="Workflow JSON file")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout in seconds")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("ComfyUI API Test")
    print("=" * 60)
    print(f"Server:   {args.base_url}")
    print(f"Workflow: {args.workflow}")
    print("=" * 60)
    
    success = test_comfy_api(args.base_url, args.workflow, args.timeout)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ TEST PASSED!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ TEST FAILED!")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
