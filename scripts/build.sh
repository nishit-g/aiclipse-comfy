#!/bin/bash
set -e

REGISTRY=${REGISTRY:-"ghcr.io/nishit-g"}
VERSION=${VERSION:-"latest"}
TARGET=${1:-"all"}

echo "🏗️ Building AiClipse templates..."
echo "📋 Registry: $REGISTRY"
echo "🏷️ Version: $VERSION"
echo "🎯 Target: $TARGET"

case $TARGET in
    "base-common")
        echo "🔨 Building base common image..."
        docker buildx bake base-common
        ;;
    "base-rtx4090")
        echo "🔨 Building RTX 4090 base image..."
        docker buildx bake base-rtx4090
        ;;
    "base-rtx5090")
        echo "🔨 Building RTX 5090 base image..."
        docker buildx bake base-rtx5090
        ;;
    "bases")
        echo "🔨 Building base images sequentially..."
        echo "1/3 Building base-common..."
        docker buildx bake base-common
        echo "2/3 Building base-rtx4090..."
        docker buildx bake base-rtx4090
        echo "3/3 Building base-rtx5090..."
        docker buildx bake base-rtx5090
        ;;
    "4090")
        echo "🔨 Building RTX 4090 stack..."
        echo "1/2 Building base-rtx4090..."
        docker buildx bake base-rtx4090
        echo "2/2 Building sd15-basic-4090..."
        docker buildx bake sd15-basic-4090
        ;;
    "5090")
        echo "🔨 Building RTX 5090 stack..."
        echo "1/2 Building base-rtx5090..."
        docker buildx bake base-rtx5090
        echo "2/2 Building sd15-basic-5090..."
        docker buildx bake sd15-basic-5090
        ;;
    "sd15-basic")
        echo "🔨 Building SD 1.5 basic templates..."
        echo "1/2 Building sd15-basic-4090..."
        docker buildx bake sd15-basic-4090
        echo "2/2 Building sd15-basic-5090..."
        docker buildx bake sd15-basic-5090
        ;;
    "all")
        echo "🔨 Building everything sequentially..."
        echo "1/5 Building base-common..."
        docker buildx bake base-common
        echo "2/5 Building base-rtx4090..."
        docker buildx bake base-rtx4090
        echo "3/5 Building base-rtx5090..."
        docker buildx bake base-rtx5090
        echo "4/5 Building sd15-basic-4090..."
        docker buildx bake sd15-basic-4090
        echo "5/5 Building sd15-basic-5090..."
        docker buildx bake sd15-basic-5090
        ;;
    *)
        echo "❌ Unknown target: $TARGET"
        echo "Usage: $0 [base-common|base-rtx4090|base-rtx5090|bases|sd15-basic|4090|5090|all]"
        exit 1
        ;;
esac

echo "✅ Build complete!"
echo "🚀 Deploy images:"
