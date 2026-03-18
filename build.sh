#!/usr/bin/env bash
# Build script for Render — builds frontend + installs backend deps
set -e

echo "==> Installing backend dependencies..."
pip install -r requirements.txt

echo "==> Installing Node.js for frontend build..."
# Render provides Node.js, but if not available, install it
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi

echo "==> Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "==> Build complete!"
echo "Frontend built to frontend/out/"
ls -la frontend/out/ 2>/dev/null || echo "Warning: frontend/out not found"
