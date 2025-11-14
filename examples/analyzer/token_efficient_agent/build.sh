#!/bin/bash
# Pre-build the Docker image for token-efficient agent

echo "Building Docker image: token-efficient-agent..."
docker build -t token-efficient-agent .

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Docker image built successfully!"
    echo ""
    echo "To use the pre-built image, run:"
    echo "  python cli.py --image token-efficient-agent"
else
    echo ""
    echo "✗ Docker build failed"
    exit 1
fi
