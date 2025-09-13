#!/bin/bash

# Activate Python virtual environment and set up environment variables
echo "Activating Python virtual environment..."
source venv/bin/activate

# Load environment variables
echo "Loading environment variables..."
export $(cat .env | grep -v '^#' | xargs)

echo "Environment activated!"
echo "Python: $(which python)"
echo "Pip: $(which pip)"
echo ""
echo "Requirements.txt has been updated with:"
echo "  - Python 3.13 compatible versions"
echo "  - Organized by category with comments"
echo "  - All dependencies with exact version pins"
echo ""
echo "To start the backend server:"
echo "  cd backend && python main.py"
echo ""
echo "To start the frontend server:"
echo "  cd frontend && npm run dev"
echo ""
echo "To reinstall from requirements:"
echo "  pip install -r backend/requirements.txt"
