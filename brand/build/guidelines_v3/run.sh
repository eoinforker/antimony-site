#!/bin/sh
# Builds the guidelines and the kit. Needs the static server on :8811 only to recapture the website's frames (cap/blendc.cjs).
set -e
cd "$(dirname "$0")"
python3 trace.py
python3 build.py assets
node render.cjs jobs/textures.json
node render.cjs jobs/exports.json
python3 build.py pages
python3 build.py finish
python3 build.py pages
