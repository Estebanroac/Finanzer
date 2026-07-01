#!/usr/bin/env bash
# Build script for Render — installs backend deps only.
#
# The frontend is a pre-built static export committed to frontend/out/ and
# served directly by FastAPI, so we do NOT rebuild it here. Running
# `npm install && npm run build` (Next.js + Turbopack) on Render is slow and
# was timing out the deploy. To ship frontend changes, rebuild locally
# (`cd frontend && npm run build`) and commit frontend/out/.
set -e

echo "==> Installing backend dependencies..."
pip install -r requirements.txt

echo "==> Verifying pre-built frontend (frontend/out/)..."
if [ -d frontend/out ] && [ -f frontend/out/index.html ]; then
    echo "frontend/out/ present — serving the committed static build."
else
    echo "ERROR: frontend/out/ is missing. Rebuild it locally with" >&2
    echo "       'cd frontend && npm run build' and commit it." >&2
    exit 1
fi

echo "==> Build complete!"
