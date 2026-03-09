#!/bin/bash

# 🚀 Launch AI Travel Planner Frontend

echo "🌍 AI Smart Travel Planning System"
echo "=================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if streamlit is installed
if ! python -c "import streamlit" 2>/dev/null; then
    echo "📥 Installing Streamlit..."
    pip install streamlit plotly
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo ""
    echo "⚙️  Please edit .env and add your OPENAI_API_KEY"
    echo "    You can also configure it in the web interface sidebar"
    echo ""
fi

# Launch Streamlit
echo "🚀 Launching Streamlit app..."
echo ""
echo "   The app will open in your browser at:"
echo "   👉 http://localhost:8501"
echo ""
echo "   Press Ctrl+C to stop the server"
echo ""

streamlit run app.py
