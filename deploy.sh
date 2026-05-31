#!/usr/bin/env bash
#
# One-time (and repeat) deploy helper for World News Hub.
# Run from inside the world-news-hub folder:  bash deploy.sh
#
# Prerequisite: create an EMPTY repo on GitHub first (no README, no
# .gitignore, no licence) named exactly "world-news-hub" under your account.
# Reuses whatever git credentials already work for your SimRacing-News repo.

set -euo pipefail

REPO="https://github.com/halvar20000/world-news-hub.git"
cd "$(dirname "$0")"

echo "==> Deploying World News Hub to $REPO"

[ -d .git ] || { echo "==> git init"; git init -q; }

git add -A
git commit -q -m "World News Hub update: $(date '+%Y-%m-%d %H:%M')" \
  || echo "==> nothing new to commit"

git branch -M main
git remote get-url origin >/dev/null 2>&1 || git remote add origin "$REPO"

# Safe on the very first push (remote empty) thanks to the guard.
git pull --rebase origin main 2>/dev/null || true

git push -u origin main

echo ""
echo "==> Pushed. Once GitHub Pages is enabled (Settings > Pages > main /docs)"
echo "    your site will be live at:"
echo "    https://halvar20000.github.io/world-news-hub/"
