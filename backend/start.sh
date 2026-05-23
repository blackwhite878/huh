#!/bin/bash
# Quick start script for Property Agent UI
# Complete end-to-end setup

set -e

echo "================================"
echo "Property Agent UI - Quick Start"
echo "================================"

# Check if Python 3.10+
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python $python_version"

# Backend setup
echo ""
echo "📦 Setting up backend..."
cd backend

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check .env
if [ ! -f ".env" ]; then
    echo "⚠️  .env not found. Copying from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your Chutes AI credentials"
fi

# Run startup checks
echo ""
echo "🔍 Running startup checks..."
python3 startup.py

# Cleanup
deactivate

