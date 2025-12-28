"""
CLI for the ComfyUI Production API.
Simple, clean pattern with unique entrypoint names.
"""

from .main import (
    app,
    download_models,
    sync_workflows,
    ui,
    api,
    test_websocket,
    ComfyUIService,
    WorkflowRequest,
)


@app.local_entrypoint()
def main(
    mode: str = "info",
    workflow: str = "txt2img",
    prompt: str = "a beautiful landscape painting",
    steps: int = 20,
    cfg: float = 7.0,
    width: int = 1024,
    height: int = 1024,
    seed: int = None,
):
    """
    Main CLI entrypoint for ComfyUI management.

    Usage Examples:
        # Get deployment info
        modal run -m comfy.cli --mode info

        # Download models from config
        modal run -m comfy.cli --mode download

        # Sync local workflows to volume
        modal run -m comfy.cli --mode sync

        # Launch development UI
        modal run -m comfy.cli --mode ui

        # Test workflow execution
        modal run -m comfy.cli --mode test --workflow txt2img --prompt "cyberpunk city"

        # Create configuration templates
        modal run -m comfy.cli --mode create-configs
    """

    print(f"🚀 Running ComfyUI command: {mode}")

    if mode == "info":
        print("🚀 ComfyUI Production API")
        print("=" * 50)
        print(f"📡 API URL: {api.web_url}")
        print(f"🎨 UI URL: {ui.web_url}")
        print("\n📋 Available commands:")
        print("  modal run -m comfy.cli --mode download")
        print("  modal run -m comfy.cli --mode sync")
        print("  modal run -m comfy.cli --mode test")
        print("  modal run -m comfy.cli --mode ui")
        print("  modal run -m comfy.cli --mode create-configs")

    elif mode == "download":
        print("📥 Starting model download process...")
        print("⏳ This may take several minutes for large models...")
        try:
            result = download_models.remote()
            print("--- ✅ Download Success ---")
            print(f"Result: {result}")
            print("---------------------------")
        except Exception as e:
            print("--- ❌ Download Failed ---")
            print(f"Error: {str(e)}")
            print("--------------------------")
            raise

    elif mode == "sync":
        print("🔄 Syncing local workflows to volume...")
        try:
            result = sync_workflows.remote()
            print("--- ✅ Sync Success ---")
            print(f"Result: {result}")
            print("----------------------")
        except Exception as e:
            print("--- ❌ Sync Failed ---")
            print(f"Error: {str(e)}")
            print("---------------------")
            raise

    elif mode == "ui":
        print("🎨 Launching ComfyUI development interface...")
        print(f"🌐 Access at: {ui.web_url}")
        print("💡 Tip: Use this to create and test workflows")
        print("⚠️  Remember to close the UI when done to avoid charges")

    elif mode == "test":
        print(f"🧪 Testing workflow: {workflow}")
        print(f"📝 Prompt: {prompt}")
        print(f"⚙️  Settings: {steps} steps, CFG {cfg}, {width}x{height}")
        if seed:
            print(f"🎲 Seed: {seed}")

        try:
            service = ComfyUIService()

            # Build parameters
            params = {
                "text": prompt,
                "6.text": prompt,  # Common text input node
                "steps": steps,
                "cfg": cfg,
                "width": width,
                "height": height,
            }

            if seed:
                params["seed"] = seed

            request = WorkflowRequest(
                workflow_id=workflow,
                params=params,
            )

            print("\n⏳ Processing...")
            result = service.execute_workflow_streaming.remote(request)

            print("--- ✅ Test Success ---")
            print(f"Result: {result}")
            print("----------------------")

        except Exception as e:
            print("--- ❌ Test Failed ---")
            print(f"Error: {str(e)}")
            print("---------------------")
            raise

    else:
        print(f"❌ Unknown mode: {mode}")
        print("Available modes: info, download, sync, ui, test, create-configs")


@app.local_entrypoint()
def test_ws(
    workflow: str = "txt2img",
    prompt: str = "a beautiful sunset over mountains",
    steps: int = 20,
    cfg: float = 7.0,
    width: int = 1024,
    height: int = 1024,
):
    """
    Test WebSocket functionality with detailed parameters.

    Usage Examples:
        # Basic test
        modal run -m comfy.cli::test_ws

        # Custom workflow and prompt
        modal run -m comfy.cli::test_ws --workflow img2img --prompt "cyberpunk city"

        # Full parameter control
        modal run -m comfy.cli::test_ws --prompt "portrait photo" --steps 30 --cfg 8.0 --width 768 --height 1024
    """
    print(f"🧪 Testing WebSocket with workflow: {workflow}")
    print(f"📝 Prompt: {prompt}")
    print(f"⚙️  Settings: {steps} steps, CFG {cfg}, {width}x{height}")

    try:
        print("\n⏳ Connecting to WebSocket API...")
        test_websocket.remote(
            workflow_id=workflow,
            prompt=prompt,
            steps=steps,
            cfg=cfg,
            width=width,
            height=height,
        )
        print("--- ✅ WebSocket Test Complete ---")
        print("---------------------------------")
    except Exception as e:
        print("--- ❌ WebSocket Test Failed ---")
        print(f"Error: {str(e)}")
        print("-------------------------------")
        raise


@app.local_entrypoint()
def deploy_app():  # CHANGED: renamed from 'deploy' to avoid conflicts
    """
    Deploy the ComfyUI application with pre-checks.

    Usage:
        modal run -m comfy.cli::deploy_app
    """
    import subprocess
    from pathlib import Path

    print("🚀 Deploying ComfyUI Production API...")
    print("=" * 50)

    # Check if config files exist
    config_dir = Path("comfy/config")
    workflows_dir = Path("workflows")

    print("🔍 Checking prerequisites...")

    if not config_dir.exists() or not (config_dir / "models.yaml").exists():
        print("--- ❌ Prerequisites Failed ---")
        print("Configuration files not found!")
        print("Run this first:")
        print("  modal run -m comfy.cli --mode create-configs")
        print("------------------------------")
        return

    if not workflows_dir.exists() or not list(workflows_dir.glob("*.json")):
        print("--- ❌ Prerequisites Failed ---")
        print("No workflow files found!")
        print("Add .json workflow files to the ./workflows/ directory")
        print("------------------------------")
        return

    print("✅ Configuration files found")
    print("✅ Workflow files found")

    try:
        print("\n📤 Deploying to Modal...")
        result = subprocess.run(
            ["modal", "deploy", "comfy/main.py"],
            capture_output=True,
            text=True,
            check=True,
        )

        print("--- ✅ Deployment Success ---")
        print(result.stdout)
        print("\n📥 Next steps:")
        print("1. Download models: modal run -m comfy.cli --mode download")
        print("2. Sync workflows: modal run -m comfy.cli --mode sync")
        print("3. Test API: modal run -m comfy.cli::test_ws")
        print("4. Access UI: modal run -m comfy.cli --mode ui")
        print("----------------------------")

    except subprocess.CalledProcessError as e:
        print("--- ❌ Deployment Failed ---")
        print(f"Error: {e}")
        print(f"Output: {e.stderr}")
        print("---------------------------")
        raise


@app.local_entrypoint()
def check_status():  # CHANGED: renamed from 'status' to avoid conflicts
    """
    Check deployment status and volume information.

    Usage:
        modal run -m comfy.cli::check_status
    """
    import subprocess

    print("📊 Checking ComfyUI deployment status...")
    print("=" * 40)

    try:
        print("🔍 Modal Apps:")
        result = subprocess.run(
            ["modal", "app", "list"], capture_output=True, text=True, check=True
        )
        print(result.stdout)

        print("\n💾 Modal Volumes:")
        result = subprocess.run(
            ["modal", "volume", "list"], capture_output=True, text=True, check=True
        )
        print(result.stdout)

        print("--- ✅ Status Check Complete ---")
        print("-------------------------------")

    except subprocess.CalledProcessError as e:
        print("--- ❌ Status Check Failed ---")
        print(f"Error: {e}")
        print("-----------------------------")
        raise


@app.local_entrypoint()
def show_logs(
    follow: bool = False, lines: int = 50, app_name: str = "comfyui-production-api"
):  # CHANGED: renamed from 'logs' to avoid conflicts
    """
    View service logs with options.

    Usage Examples:
        # View recent logs
        modal run -m comfy.cli::show_logs

        # Follow logs in real-time
        modal run -m comfy.cli::show_logs --follow True

        # View more lines
        modal run -m comfy.cli::show_logs --lines 100

        # Different app name
        modal run -m comfy.cli::show_logs --app-name my-comfyui-app
    """
    import subprocess

    print(f"📋 Viewing logs for {app_name}")
    print(f"📊 Lines: {lines}, Follow: {follow}")
    print("=" * 40)

    try:
        cmd = ["modal", "logs"]

        if follow:
            cmd.append("--follow")
        else:
            cmd.extend(["--lines", str(lines)])

        cmd.append(app_name)

        subprocess.run(cmd, check=True)

    except subprocess.CalledProcessError as e:
        print("--- ❌ Log Viewing Failed ---")
        print(f"Error: {e}")
        print("App might not be deployed or name is incorrect")
        print("----------------------------")
        raise


@app.local_entrypoint()
def generate_image(
    prompt: str,
    workflow: str = "txt2img",
    steps: int = 20,
    cfg: float = 7.0,
    width: int = 1024,
    height: int = 1024,
    seed: int = None,
    output_dir: str = "output",
):  # CHANGED: renamed from 'generate' to avoid conflicts
    """
    Generate an image using the deployed ComfyUI API.

    Usage Examples:
        # Simple generation
        modal run -m comfy.cli::generate_image --prompt "a beautiful landscape"

        # With custom parameters
        modal run -m comfy.cli::generate_image --prompt "cyberpunk city" --steps 30 --cfg 8.0

        # Portrait orientation
        modal run -m comfy.cli::generate_image --prompt "portrait photo" --width 768 --height 1024

        # With specific seed
        modal run -m comfy.cli::generate_image --prompt "consistent style" --seed 42
    """
    from pathlib import Path
    import time

    print("🎨 Generating image with ComfyUI")
    print("=" * 40)
    print(f"📝 Prompt: {prompt}")
    print(f"🎯 Workflow: {workflow}")
    print(f"⚙️  Settings: {steps} steps, CFG {cfg}, {width}x{height}")
    if seed:
        print(f"🎲 Seed: {seed}")

    try:
        service = ComfyUIService()

        # Build parameters
        params = {
            "text": prompt,
            "6.text": prompt,  # Common text input node
            "steps": steps,
            "cfg": cfg,
            "width": width,
            "height": height,
        }

        if seed:
            params["seed"] = seed

        request = WorkflowRequest(
            workflow_id=workflow,
            params=params,
        )

        print("\n⏳ Processing image generation...")
        start_time = time.time()

        # This should return image bytes
        result = service.execute_workflow_streaming.remote(request)

        # Save the result if it's image bytes
        if isinstance(result, bytes):
            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)

            # Generate filename
            timestamp = int(time.time())
            safe_prompt = "".join(
                c for c in prompt if c.isalnum() or c in (" ", "-", "_")
            ).strip()[:30]
            filename = f"{safe_prompt}_{timestamp}.png"

            file_path = output_path / filename
            file_path.write_bytes(result)

            duration = time.time() - start_time

            print("--- ✅ Generation Success ---")
            print(f"💾 Saved: {file_path}")
            print(f"⏱️  Duration: {duration:.1f}s")
            print("----------------------------")
        else:
            print("--- ⚠️  Generation Result ---")
            print(f"Result: {result}")
            print("Note: Expected image bytes, got different result type")
            print("----------------------------")

    except Exception as e:
        print("--- ❌ Generation Failed ---")
        print(f"Error: {str(e)}")
        print("Check that the API is deployed and workflow exists")
        print("--------------------------")
        raise
