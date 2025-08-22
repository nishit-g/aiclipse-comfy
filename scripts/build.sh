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
    "bases")
        echo "🔨 Building base images..."
        docker buildx bake bases --push
        ;;
    "4090")
        echo "🔨 Building RTX 4090 stack..."
        docker buildx bake base-rtx4090 headshots-4090 --push
        ;;
    "5090")
        echo "🔨 Building RTX 5090 stack..."
        docker buildx bake base-rtx5090 headshots-5090 --push
        ;;
    "sd15-basic")
        echo "🔨 Building SD 1.5 basic templates..."
        docker buildx bake sd15-basic --push
        ;;
    "all")
        echo "🔨 Building everything..."
        docker buildx bake all --push
        ;;
    *)
        echo "❌ Unknown target: $TARGET"
        echo "Usage: $0 [bases|sd15-basic|4090|5090|all]"
        exit 1
        ;;
esac

echo "✅ Build complete!"
echo "🚀 Deploy images:"
