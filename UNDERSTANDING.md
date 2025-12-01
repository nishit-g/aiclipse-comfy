# Understanding the AiClipse ComfyUI Setup

## 1. COMFY_ARGS Issue
**Observation:**
- `start.sh` checks for `COMFY_ARGS` and appends it to the startup command.
- However, `COMFY_ARGS` is **NOT** included in the `SAFE_VARS` list in `setup_environment`.
- This means it is not exported to `/etc/rp_environment`, so it won't be available in SSH sessions or if the user tries to run commands manually after logging in.
- For the main process (PID 1), it *should* work if set in the container environment (e.g., via RunPod UI).
- The user reported "if its there use that else dont". The current logic does exactly that (appends if set).
- **Hypothesis:** The user might be expecting `COMFY_ARGS` to persist in their shell sessions, or there's a misunderstanding of how it's applied.
- **Fix:** Add `COMFY_ARGS` to `SAFE_VARS` in `start.sh`.

## 2. R2 Model Downloads
**Observation:**
- `setup_models.sh` is the active downloader script used by `start.sh`.
- It uses `aria2c` for high-performance parallel downloads.
- **Critical Gap:** `setup_models.sh` **ONLY** supports `huggingface`, `civitai`, and `url/direct`. It explicitly ignores or warns on other sources.
- `download_models.py` exists in `scripts/` and **HAS** full R2 support (using `boto3`), but it is **NOT** currently used by the startup sequence.
- **Fix:** Integrate `download_models.py` into the startup flow.
    - **Option A:** Replace `setup_models.sh` logic with `download_models.py` (slower, sequential downloads unless updated).
    - **Option B (Recommended):** Hybrid approach. Update `setup_models.sh` to:
        1. Generate `aria2_input` for HF/CivitAI/URL (keep fast downloads).
        2. Generate a separate manifest for R2 entries.
        3. Call `download_models.py` to handle the R2 manifest.

## 3. Visualizing the Workspace (Symlinks)

You asked for a visual explanation. Here is how the folders are wired up.

**The Concept:**
We treat `/workspace/aiclipse` as the **Real Storage Vault**. This is the *only* folder that needs to be persistent. Everything else is just a "shortcut" (symlink) pointing to it.

**Directory Structure:**

```text
/workspace/                  <-- The Root Folder you see
│
├── aiclipse/                <-- 🟢 REAL STORAGE (The Vault)
│   │                            (Mount your persistent disk here)
│   │
│   ├── ComfyUI/             <-- The actual ComfyUI installation
│   │   ├── custom_nodes/
│   │   ├── input/
│   │   └── output/
│   │
│   ├── models/              <-- Where models actually live
│   ├── workflows/           <-- Your saved workflows
│   └── logs/
│
│   ▼ ▼ ▼  SYMLINKS (Shortcuts) ▼ ▼ ▼
│
├── ComfyUI       ---------> Points to ./aiclipse/ComfyUI
├── models        ---------> Points to ./aiclipse/models
├── workflows     ---------> Points to ./aiclipse/workflows
├── input         ---------> Points to ./aiclipse/ComfyUI/input
├── output        ---------> Points to ./aiclipse/ComfyUI/output
├── logs          ---------> Points to ./aiclipse/logs
└── custom_nodes  ---------> Points to ./aiclipse/ComfyUI/custom_nodes
```

**Why do we do this?**
1.  **One Mount Point:** You only need to save/mount `/workspace/aiclipse` to back up *everything* (ComfyUI, Models, Nodes, Outputs).
2.  **Convenience:** When you open the terminal, you see `models`, `input`, `output` right there in the root. You don't have to dig into subfolders.
3.  **Safety:** If you mess up the shortcuts, the real data in `aiclipse/` is safe.

**Verdict:**
This is a **Great Structure**. It gives you the best of both worlds: a clean workspace and a single, easy-to-backup data folder.

## 4. Visual Summary of Improvements

We have significantly upgraded the system. Here is the visual breakdown of what we changed.

### A. The "Hybrid" Downloader
We now use the best tool for the job.

```text
Manifest File (models_manifest.txt)
       │
       ▼
   [ Splitter Logic ]
   │                │
   │ (Standard)     │ (Private/R2)
   ▼                ▼
[ Aria2c ]      [ Python Script ]
   │                │
   │ (Fast/Parallel)│ (Authenticated)
   │                │
   └───────┬────────┘
           ▼
    /workspace/aiclipse/models
```

### B. Workflow Protection
We stopped the "Overwrite" behavior.

```text
BEFORE:
Template Workflows  ─────(Overwrite)────▶  Your Workflows
(You lose your edits on restart) ❌

AFTER:
Template Workflows  ─────(Copy if Missing)────▶  Your Workflows
(Your edits are SAFE) ✅
```

### C. Robust Model Linking
We simplified how ComfyUI finds models.

```text
BEFORE:
extra_model_paths.yaml  (Hardcoded List)
   ├── checkpoints: ...
   ├── loras: ...
   └── (If you add 'ipadapter', it fails) ❌

AFTER:
ComfyUI/models  ──(Symlink)──▶  /workspace/aiclipse/models
   │
   └── (Any folder you create here is automatically seen) ✅
```

### D. Environment Fix (COMFY_ARGS)
We ensured your custom arguments survive.

```text
RunPod Variable (COMFY_ARGS)
       │
       ▼
   [ start.sh ] ──(Export)──▶ /etc/rp_environment
                                     │
                                     ▼
                              [ SSH Session ]
                              [ ComfyUI Process ]
                              (It works everywhere now) ✅
```

### E. Migration Safety (The "Empty Folder" Fear)
You asked: *"Won't it break if there are no folders yet?"*
Answer: **No, because we copy them first.**

```text
Fresh Container Start:
1. ComfyUI comes with default empty folders (checkpoints/, loras/, etc.)
2. Script sees this and copies them to /workspace/aiclipse/models
   [ ComfyUI/models/* ] ──(Copy)──▶ [ /workspace/aiclipse/models/ ]
3. THEN it creates the symlink.

Result: /workspace/aiclipse/models is NEVER empty. It always has the basics.
```

### F. R2 Configuration (Environment Variables)
To enable R2 downloads, you must set these environment variables in RunPod (or your `.env` file):

| Variable | Description |
| :--- | :--- |
| `R2_ACCESS_KEY_ID` | Your Cloudflare R2 Access Key ID |
| `R2_SECRET_ACCESS_KEY` | Your Cloudflare R2 Secret Access Key |
| `R2_ACCOUNT_ID` | Your Cloudflare Account ID |
| `R2_BUCKET` | (Optional) Default bucket name if not specified in manifest |

### G. The COMFY_ARGS Flow
How your custom arguments get to ComfyUI:

1.  **Dockerfile:** Sets default `ENV COMFY_ARGS="..."`.
2.  **RunPod UI:** You can override `COMFY_ARGS` here. This new value replaces the Dockerfile default.
3.  **start.sh:**
    -   Reads `COMFY_ARGS` (from RunPod or Dockerfile).
    -   **Exports** it to `/etc/rp_environment` (so it persists in SSH).
    -   **Appends** it to the python command: `python main.py ... $COMFY_ARGS`.

## 6. Final Review (Green Light) ✅
I have performed a comprehensive review of the entire system.

1.  **Dependencies:** `boto3` (required for R2) is correctly installed in the `/venv` environment in the base Dockerfile.
2.  **Execution:** I updated the scripts to explicitly use `/venv/bin/python` to guarantee they use the environment with `boto3` installed.
3.  **Safety:** The "Migration Safety" check ensures you won't lose default models.
4.  **Persistence:** The "Workflow Protection" ensures you won't lose your work.

**System Status:** READY FOR DEPLOYMENT.

## 5. Plan (Completed)
1.  **Modify `start.sh`**: Add `COMFY_ARGS` to `SAFE_VARS`. (Done)
2.  **Update `setup_models.sh`**: Implement the hybrid download approach. (Done)
3.  **Refactor Model Paths**: Switched to directory symlink. (Done)
4.  **Fix Workflow Sync**: Implemented no-clobber copy. (Done)
5.  **Documentation**: Visualized improvements and documented R2 vars. (Done)
6.  **Final Polish**: Standardized python paths. (Done)


