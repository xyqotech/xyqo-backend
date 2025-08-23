#!/bin/bash
# Start XYQO Backend with environment variables

cd /Users/bassiroudiop/autopilot-demo

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Activate virtual environment
source venv/bin/activate

# Start the backend
echo "🚀 Starting XYQO Backend with OpenAI integration..."
echo "📊 OpenAI API Key: ${OPENAI_API_KEY:0:10}..."

python xyqo_backend.py
