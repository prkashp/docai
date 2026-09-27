#!/bin/bash

echo "=== OCR Pipeline Setup Verification ==="
echo ""

# Check Docker
echo "[1] Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found"
else
    docker_version=$(docker --version)
    echo "✓ $docker_version"
fi

# Check Docker Compose
echo ""
echo "[2] Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found"
else
    compose_version=$(docker-compose --version)
    echo "✓ $compose_version"
fi

# Check required files
echo ""
echo "[3] Checking required files..."
files=("Dockerfile" "docker-compose.yml" "requirements.txt" ".env.example")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "❌ $file missing"
    fi
done

# Check directories
echo ""
echo "[4] Checking directories..."
dirs=("src" "images")
for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "✓ $dir/"
    else
        echo "❌ $dir/ missing"
    fi
done

# Check Python files
echo ""
echo "[5] Checking Python source files..."
py_files=("src/ocr.py" "src/vectorstore.py" "src/ingest.py" "src/search.py")
for file in "${py_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "❌ $file missing"
    fi
done

echo ""
echo "=== Setup Verification Complete ==="
echo ""
echo "Next steps:"
echo "1. Place scanned images in the 'images/' directory"
echo "2. Run: docker compose up -d --build"
echo "3. Run: docker compose exec app python src/ingest.py"
echo "4. Run: docker compose exec app python src/search.py 'your query'"
