#!/bin/bash
echo "🔧 Rebuilding Tax Deduction Finder Backend..."
echo "============================================="
echo ""

cd /mnt/c/Users/khayatimittal/Downloads/tax_deduction_finder-20260418T111013Z-3-001/tax_deduction_finder

echo "📦 Stopping containers..."
docker compose down

echo ""
echo "🏗️  Building backend (this may take 5-10 minutes)..."
docker compose build backend --no-cache

echo ""
echo "🚀 Starting containers..."
docker compose up -d

echo ""
echo "✅ Done! Watching logs..."
echo "   Press Ctrl+C to stop watching"
echo ""
docker compose logs -f backend
