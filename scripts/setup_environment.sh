#!/bin/bash
# Optimizer V3 Environment Setup Script
# Task 0.1: Package Requirements & Dependencies

set -e  # Exit on error

echo "=============================================================================="
echo "OPTIMIZER V3 - ENVIRONMENT SETUP"
echo "Task 0.1: Package Requirements & Dependencies"
echo "=============================================================================="
echo ""

# Check Python version
echo "📌 Checking Python version..."
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.10"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "❌ Python 3.10+ required (found $python_version)"
    exit 1
fi
echo "✅ Python $python_version found"
echo ""

# Check if Poetry is installed
echo "📌 Checking for Poetry..."
if ! command -v poetry &> /dev/null; then
    echo "⚠️  Poetry not found. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    
    # Add Poetry to PATH for current session
    export PATH="$HOME/.local/bin:$PATH"
    
    echo "✅ Poetry installed"
else
    poetry_version=$(poetry --version)
    echo "✅ $poetry_version found"
fi
echo ""

# Install dependencies with Poetry
echo "📦 Installing dependencies with Poetry..."
poetry install
echo "✅ Dependencies installed"
echo ""

# Validate installation
echo "🧪 Validating dependencies..."
poetry run python scripts/validate_dependencies.py
echo ""

# Install pre-commit hooks
echo "🔧 Installing pre-commit hooks..."
if poetry run pre-commit install; then
    echo "✅ Pre-commit hooks installed"
else
    echo "⚠️  Pre-commit hooks not installed (optional)"
fi
echo ""

# Create necessary directories
echo "📁 Creating project directories..."
mkdir -p data/raw
mkdir -p data/processed
mkdir -p logs
mkdir -p config
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p docs/database
echo "✅ Directories created"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ .env file created (please update with your settings)"
    else
        echo "⚠️  .env.example not found, skipping .env creation"
    fi
else
    echo "✅ .env file already exists"
fi
echo ""

echo "=============================================================================="
echo "✅ ENVIRONMENT SETUP COMPLETE"
echo "=============================================================================="
echo ""
echo "Next steps:"
echo "1. Update .env file with your PostgreSQL credentials"
echo "2. Run: poetry shell (to activate virtual environment)"
echo "3. Continue with Task 0.2: Install and Configure PostgreSQL"
echo ""
