#!/bin/bash
# Kinetic Empire Unified Trading System Startup Script

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ No virtual environment found (.venv or venv)"
    exit 1
fi

# Set PYTHONPATH to include the project root
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Parse command line arguments
USE_LEGACY=false
for arg in "$@"; do
    case $arg in
        --legacy)
            USE_LEGACY=true
            shift
            ;;
    esac
done

# Run the appropriate bot
if [ "$USE_LEGACY" = true ]; then
    echo "🚀 Starting Kinetic Empire Trading Bot (Legacy Mode)..."
    python run_bot.py "$@"
else
    echo "🚀 Starting Kinetic Empire Unified Trading System..."
    echo "   (Use --legacy flag to run the old single-engine bot)"
    python main.py "$@"
fi
