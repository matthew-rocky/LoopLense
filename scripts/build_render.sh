#!/usr/bin/env bash
set -e

echo "Building LoopLens frontend..."
cd frontend
npm install
npm run build
cd ..

echo "Frontend build complete."
