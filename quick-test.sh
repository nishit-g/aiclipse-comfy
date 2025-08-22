#!/bin/bash
# Quick test commands to run after applying all fixes

echo "🧪 AiClipse Quick Test Suite"
echo "============================"

# 1. Validate project structure
echo "1️⃣ Validating project..."
./scripts/validate.sh

# 2. Test build configuration
echo ""
echo "2️⃣ Testing build configuration..."
docker buildx bake --print > /dev/null && echo "✅ Build config valid" || echo "❌ Build config invalid"

# 3. Test model download script
echo ""
echo "3️⃣ Testing model download script..."
python3 base/scripts/download_models.py --manifest templates/sd15-basic/models_manifest.txt --models-dir /tmp/test --validate-only && echo "✅ Model script valid" || echo "❌ Model script invalid"

# 4. Test script syntax
echo ""
echo "4️⃣ Testing script syntax..."
for script in base/scripts/*.sh scripts/*.sh; do
    [ -f "$script" ] || continue
    if bash -n "$script"; then
        echo "✅ $script syntax OK"
    else
        echo "❌ $script syntax ERROR"
    fi
done

# 5. Build and test (if Docker available)
if command -v docker &> /dev/null; then
    echo ""
    echo "5️⃣ Testing Docker build..."
    echo "Run these commands to build and test:"
    echo ""
    echo "# Build base images:"
    echo "./scripts/build.sh bases"
    echo ""
    echo "# Build template:"
    echo "./scripts/build.sh sd15-basic"
    echo ""
    echo "# Test everything:"
    echo "./scripts/test.sh all"
else
    echo ""
    echo "5️⃣ Docker not available - skipping build test"
fi

echo ""
echo "🎯 Next steps:"
echo "1. Fix any errors shown above"
echo "2. Run: ./scripts/build.sh bases"
echo "3. Run: ./scripts/build.sh sd15-basic"
echo "4. Run: ./scripts/test.sh all"
echo "5. Push to GitHub!"
