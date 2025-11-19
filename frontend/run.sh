#!/bin/bash
# Quick start script for frontend

echo "🚀 Starting AutoTest-RL Frontend Dashboard..."
echo

# Check if in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Not in a virtual environment"
    echo "   Consider creating one: python -m venv venv && source venv/bin/activate"
    echo
fi

# Check if dependencies are installed
if ! python -c "import streamlit" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    echo
fi

# Set default API URL if not set
if [ -z "$API_BASE_URL" ]; then
    export API_BASE_URL="http://localhost:8000"
    echo "🔗 Using default API URL: $API_BASE_URL"
    echo
fi

# Run Streamlit
echo "✅ Starting Streamlit on http://localhost:8501"
echo
streamlit run app.py
