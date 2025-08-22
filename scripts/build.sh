#!/bin/bash

TEMPLATE=$1
CLIENT=${2:-default}
REGISTRY="ghcr.io/nishit-g"

if [ -z "$TEMPLATE" ]; then
    echo "Usage: ./build.sh <template> [client]"
    echo "Available templates:"
    ls templates/
    exit 1
fi

echo "🏗️ Building $TEMPLATE for $CLIENT..."

# Build base image first
echo "📦 Building base image..."
docker build --platform=linux/amd64 -t aiclipse/comfy-base:latest base/

# Build template
echo "🔨 Building template..."
docker build --platform=linux/amd64 \
    -t aiclipse/comfy-$TEMPLATE:$CLIENT \
    templates/$TEMPLATE/

# Tag for registry
docker tag aiclipse/comfy-$TEMPLATE:$CLIENT $REGISTRY/aiclipse-$TEMPLATE:$CLIENT

echo "✅ Built: $REGISTRY/aiclipse-$TEMPLATE:$CLIENT"
echo "🚀 Push with: docker push $REGISTRY/aiclipse-$TEMPLATE:$CLIENT"
