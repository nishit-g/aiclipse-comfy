#!/bin/bash
set -e

REGISTRY=${REGISTRY:-"ghcr.io/yourusername"}
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
    "headshots")
        echo "🔨 Building headshots templates..."
        docker buildx bake headshots --push
        ;;
    "4090")
        echo "🔨 Building RTX 4090 stack..."
        docker buildx bake base-rtx4090 headshots-4090 --push
        ;;
    "5090")
        echo "🔨 Building RTX 5090 stack..."
        docker buildx bake base-rtx5090 headshots-5090 --push
        ;;
    "all")
        echo "🔨 Building everything..."
        docker buildx bake all --push
        ;;
    *)
        echo "❌ Unknown target: $TARGET"
        echo "Usage: $0 [bases|headshots|4090|5090|all]"
        exit 1
        ;;
esac

echo "✅ Build complete!"
echo "🚀 Deploy images:"
echo "   RTX 4090: $REGISTRY/aiclipse-headshots:rtx4090-$VERSION"
echo "   RTX 5090: $REGISTRY/aiclipse-headshots:rtx5090-$VERSION"
