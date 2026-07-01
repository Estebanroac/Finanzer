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
if [ ! -d frontend/out ] || [ ! -f frontend/out/index.html ]; then
    echo "ERROR: frontend/out/ is missing. Rebuild it locally with" >&2
    echo "       'cd frontend && npm run build' and commit it." >&2
    exit 1
fi
echo "frontend/out/ present — serving the committed static build."

# Integrity guard: every CSS/JS chunk the HTML references MUST exist on disk.
# A missing chunk (e.g. dropped by .gitignore) would 404 at runtime and break
# the site silently — fail the deploy loudly here instead.
echo "==> Validating referenced static assets exist..."
MISSING=0
for html in frontend/out/index.html frontend/out/stock/index.html frontend/out/404.html; do
    [ -f "$html" ] || continue
    for asset in $(grep -oE '/_next/static/[^"]+\.(css|js)' "$html" | sort -u); do
        if [ ! -f "frontend/out${asset}" ]; then
            echo "ERROR: referenced asset missing from build: ${asset} (from ${html})" >&2
            MISSING=$((MISSING + 1))
        fi
    done
done
if [ "$MISSING" -gt 0 ]; then
    echo "ERROR: ${MISSING} referenced asset(s) missing — the committed frontend/out/ is incomplete." >&2
    echo "       Rebuild locally ('cd frontend && npm run build') and commit ALL of frontend/out/." >&2
    echo "       Check for dropped files: git status --porcelain frontend/out | grep '^??'" >&2
    exit 1
fi
echo "All referenced static assets present."

echo "==> Build complete!"
