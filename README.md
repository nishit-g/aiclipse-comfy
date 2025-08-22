# AiClipse ComfyUI Templates

> Professional-grade ComfyUI templates for RunPod with automated builds, storage integrations, and enterprise features.

[![Build All Templates](https://github.com/yourusername/aiclipse-comfyui-templates/actions/workflows/build-all-templates.yml/badge.svg)](https://github.com/yourusername/aiclipse-comfyui-templates/actions/workflows/build-all-templates.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Quick Start

### Option 1: Use Pre-built Templates (Recommended)

1. **Go to RunPod Console** → Templates → Create Template
2. **Container Image:** `ghcr.io/yourusername/aiclipse-headshots:latest`
3. **Environment Variables:**
   ```
   PUBLIC_KEY=ssh-ed25519 AAAAC3... your-ssh-key-here
   TEMPLATE_TYPE=headshots
   DOWNLOAD_MODELS=true
   ```
4. **Exposed Ports:** `8188, 8080, 8888, 22`
5. **Container Disk:** `50GB+`
6. **Network Volume:** Attach for persistence
7. **Deploy!**

### Option 2: Build Locally

```bash
git clone https://github.com/yourusername/aiclipse-comfyui-templates.git
cd aiclipse-comfyui-templates
chmod +x scripts/build.sh
./scripts/build.sh headshots latest
```

## 📦 Available Templates

| Template | Container Image | Use Case | Status |
|----------|-----------------|----------|---------|
| **Headshots** | `ghcr.io/yourusername/aiclipse-headshots:latest` | Professional portraits, face swapping, enhancement | ✅ Ready |
| **Products** | `ghcr.io/yourusername/aiclipse-products:latest` | Product photography, e-commerce images | 🚧 In Progress |
| **Logos** | `ghcr.io/yourusername/aiclipse-logos:latest` | Logo design, brand assets | 🚧 In Progress |

## 🎯 Features

### 🔧 Core Features
- **One-click deployment** on RunPod
- **Automated model downloads** based on use case
- **Network volume support** for persistent storage
- **SSH access** with public key authentication
- **FileBrowser** for easy file management (Port 8080)
- **ComfyUI Manager** pre-installed
- **Virtual environments** with fast `uv` package manager

### 🌐 Web Interfaces
- **Port 8188** - ComfyUI Interface
- **Port 8080** - FileBrowser (file management)
- **Port 8888** - JupyterLab (optional)
- **Port 22** - SSH Access

### ☁️ Storage Integrations
- **Cloudflare R2** - Zero egress fees
- **AWS S3** - Traditional cloud storage
- **Google Cloud Storage** - Enterprise storage
- **Network Volumes** - RunPod persistent storage

### 🛡️ Enterprise Ready
- **Automated builds** with GitHub Actions
- **Multi-platform support** (linux/amd64)
- **Build caching** for faster deployments
- **Version tagging** with commit SHAs
- **Client-specific customization**

## 🗂️ Project Structure

```
aiclipse-comfyui-templates/
├── 📁 base/                    # Base ComfyUI image
│   ├── Dockerfile
│   ├── runpod.yaml
│   ├── start.sh
│   └── README.md
├── 📁 templates/               # Use case specific templates
│   ├── headshots/
│   │   ├── Dockerfile
│   │   ├── download_models.sh
│   │   └── workflows/
│   ├── products/
│   └── logos/
├── 📁 scripts/                 # Build and deployment scripts
│   ├── build.sh
│   └── deploy.sh
├── 📁 storage/                 # Storage integration scripts
│   ├── r2.sh
│   └── sync.sh
├── 📁 .github/workflows/       # CI/CD automation
│   └── build-all-templates.yml
└── README.md
```

## 🔧 Environment Variables

### Required
| Variable | Description | Example |
|----------|-------------|---------|
| `PUBLIC_KEY` | SSH public key for secure access | `ssh-ed25519 AAAAC3...` |
| `TEMPLATE_TYPE` | Template identifier | `headshots`, `products`, `logos` |

### Optional
| Variable | Description | Default |
|----------|-------------|---------|
| `DOWNLOAD_MODELS` | Auto-download models on startup | `true` |
| `JUPYTER_TOKEN` | JupyterLab access token | `""` (no auth) |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 access key | - |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 secret key | - |
| `R2_BUCKET` | R2 bucket name | - |
| `R2_ACCOUNT_ID` | R2 account ID | - |

## 🗄️ Network Volume Structure

When using RunPod Network Volumes, your data is organized as:

```
/workspace/
└── aiclipse/
    ├── ComfyUI/              # Main ComfyUI installation
    │   ├── .venv/            # Python virtual environment
    │   ├── models/           # AI models
    │   │   ├── checkpoints/
    │   │   ├── loras/
    │   │   ├── controlnet/
    │   │   └── vae/
    │   ├── custom_nodes/     # Custom nodes and extensions
    │   ├── output/           # Generated images
    │   └── workflows/        # Saved workflows
    └── filebrowser.db        # FileBrowser configuration
```

## 🔨 Development Guide

### Prerequisites
- Docker installed
- GitHub account
- RunPod account (for deployment)

### Building Templates

```bash
# Build specific template
./scripts/build.sh headshots client-name

# Build all templates
./scripts/build.sh headshots latest
./scripts/build.sh products latest
./scripts/build.sh logos latest
```

### Adding New Templates

1. **Create template directory:**
   ```bash
   mkdir templates/your-template
   ```

2. **Create Dockerfile:**
   ```dockerfile
   ARG BASE_IMAGE=ghcr.io/yourusername/aiclipse-base:latest
   FROM ${BASE_IMAGE}

   ENV TEMPLATE_TYPE=your-template
   COPY download_models.sh /download_models.sh
   RUN chmod +x /download_models.sh
   ```

3. **Create model download script:**
   ```bash
   #!/bin/bash
   COMFY_DIR=$1
   echo "📥 Downloading models for your-template..."
   # Add your model downloads here
   ```

4. **Update GitHub Actions:**
   Add your template to the matrix in `.github/workflows/build-all-templates.yml`:
   ```yaml
   strategy:
     matrix:
       template: [headshots, products, logos, your-template]
   ```

### Local Testing

```bash
# Build and test locally
./scripts/build.sh your-template test

# Run container
docker run -p 8188:8188 -p 8080:8080 \
  -e TEMPLATE_TYPE=your-template \
  aiclipse/comfy-your-template:test
```

## ☁️ Storage Integration

### Cloudflare R2 Setup

1. **Create R2 bucket** in Cloudflare dashboard
2. **Generate API tokens** with R2 permissions
3. **Add environment variables:**
   ```
   R2_ACCESS_KEY_ID=your_access_key
   R2_SECRET_ACCESS_KEY=your_secret_key
   R2_BUCKET=your_bucket_name
   R2_ACCOUNT_ID=your_account_id
   ```

4. **Use R2 commands:**
   ```bash
   # Upload outputs to R2
   r2-sync /workspace/aiclipse/ComfyUI/output outputs/$(date +%Y%m%d)

   # Download shared models from R2
   r2-download shared-models /workspace/aiclipse/ComfyUI/models
   ```

### Network Volume Best Practices

- **Minimum size:** 100GB for basic usage
- **Recommended:** 500GB+ for multiple models
- **Backup strategy:** Sync important data to R2/S3
- **Performance:** Use NVMe volumes when available

## 🔐 SSH Access Guide

### Setting up SSH Keys

1. **Generate SSH key pair:**
   ```bash
   ssh-keygen -t ed25519 -C "your-email@example.com"
   ```

2. **Copy public key:**
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```

3. **Add to RunPod environment variables:**
   ```
   PUBLIC_KEY=ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIxxxxx your-email@example.com
   ```

### Connecting via SSH

```bash
# Find your pod's SSH command in RunPod console
ssh root@pod-ip -p 22 -i ~/.ssh/id_ed25519

# Or use the proxy method
ssh root@ssh.runpod.io -p pod-port -i ~/.ssh/id_ed25519
```

### SSH Tips

- **File transfers:** Use `scp` or `rsync` instead of web uploads
- **Screen/tmux:** Keep processes running after disconnect
- **VS Code:** Use Remote-SSH extension for direct editing

## 🚀 Deployment Strategies

### Development Workflow

1. **Local development** with Docker
2. **Push to GitHub** → Automatic builds
3. **Test on RunPod** with latest images
4. **Tag releases** for production

### Production Deployment

1. **Use specific tags** instead of `latest`
2. **Attach network volumes** for data persistence
3. **Set up monitoring** with health checks
4. **Configure auto-scaling** based on demand

### Client Customization

```bash
# Build client-specific image
./scripts/build.sh headshots client-acme

# Deploy with custom branding
docker build --build-arg CLIENT_NAME=acme \
  -t aiclipse/comfy-headshots:acme \
  templates/headshots/
```

## 📊 Monitoring & Maintenance

### Health Checks

- **ComfyUI:** `http://localhost:8188/`
- **FileBrowser:** `http://localhost:8080/`
- **GPU Status:** Check via Crystools nodes

### Logs Access

```bash
# ComfyUI logs
tail -f /workspace/aiclipse/ComfyUI/comfyui.log

# Container logs via RunPod console
# Or via SSH: docker logs container-name
```

### Updates

- **Base image:** Rebuild automatically via GitHub Actions
- **Models:** Update download scripts and rebuild
- **Custom nodes:** Update via ComfyUI Manager interface

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch:** `git checkout -b feature/new-template`
3. **Make changes** and test locally
4. **Submit pull request** with clear description

### Guidelines

- **Follow naming conventions** (kebab-case for directories)
- **Test all templates** before submitting
- **Update documentation** for new features
- **Use semantic versioning** for releases

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/aiclipse-comfyui-templates/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/aiclipse-comfyui-templates/discussions)
- **RunPod Discord:** [RunPod Community](https://discord.gg/runpod)

## 🙏 Acknowledgments

- **RunPod Team** - Cloud GPU infrastructure
- **ComfyUI Community** - Amazing interface and nodes
- **Stability AI** - Stable Diffusion models
- **Hugging Face** - Model hosting and distribution

---

**Built with ❤️ by AiClipse Team**

*Empowering creative professionals with cutting-edge AI tools.*
