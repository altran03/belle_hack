#!/usr/bin/env python3
"""
Test script to verify BugSniper Pro setup
"""

import os
import sys
import subprocess
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and print status"""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (MISSING)")
        return False

def check_python_packages():
    """Check if required Python packages are installed"""
    required_packages = [
        'fastapi', 'uvicorn', 'sqlalchemy', 'pydantic', 
        'httpx', 'git', 'google.generativeai'
    ]
    
    print("\n📦 Checking Python packages...")
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (NOT INSTALLED)")
            missing_packages.append(package)
    
    return len(missing_packages) == 0

def check_node_modules():
    """Check if Node.js dependencies are installed"""
    frontend_path = Path("frontend")
    node_modules = frontend_path / "node_modules"
    
    if node_modules.exists():
        print("✅ Node.js dependencies installed")
        return True
    else:
        print("❌ Node.js dependencies not installed")
        return False

def check_env_file():
    """Check environment configuration"""
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if env_file.exists():
        print("✅ .env file exists")
        
        # Check for required variables
        with open(env_file, 'r') as f:
            content = f.read()
            
        required_vars = [
            'GEMINI_API_KEY', 'GITHUB_CLIENT_ID', 
            'GITHUB_CLIENT_SECRET', 'GITHUB_WEBHOOK_SECRET'
        ]
        
        missing_vars = []
        for var in required_vars:
            if f"{var}=" not in content or f"{var}=your_" in content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️  Please configure these variables in .env: {', '.join(missing_vars)}")
            return False
        else:
            print("✅ Environment variables configured")
            return True
    else:
        print("❌ .env file not found")
        if env_example.exists():
            print("💡 Copy env.example to .env and configure it")
        return False

def main():
    """Run all checks"""
    print("🐛 BugSniper Pro Setup Verification")
    print("=" * 50)
    
    # Check file structure
    print("\n📁 Checking file structure...")
    files_to_check = [
        ("backend/main.py", "Backend main file"),
        ("backend/requirements.txt", "Backend dependencies"),
        ("frontend/package.json", "Frontend package file"),
        ("frontend/pages/index.tsx", "Frontend main page"),
        ("sample_repo/main.py", "Sample repository"),
        ("README.md", "Documentation"),
        ("env.example", "Environment template")
    ]
    
    all_files_exist = True
    for file_path, description in files_to_check:
        if not check_file_exists(file_path, description):
            all_files_exist = False
    
    # Check dependencies
    python_ok = check_python_packages()
    node_ok = check_node_modules()
    
    # Check environment
    env_ok = check_env_file()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Setup Summary:")
    print(f"Files: {'✅' if all_files_exist else '❌'}")
    print(f"Python packages: {'✅' if python_ok else '❌'}")
    print(f"Node.js packages: {'✅' if node_ok else '❌'}")
    print(f"Environment: {'✅' if env_ok else '❌'}")
    
    if all_files_exist and python_ok and node_ok and env_ok:
        print("\n🎉 Setup looks good! You can start BugSniper Pro with:")
        print("   ./start.sh")
    else:
        print("\n⚠️  Setup incomplete. Please fix the issues above.")
        print("\nQuick setup:")
        print("1. Copy env.example to .env and configure it")
        print("2. Install Python dependencies: cd backend && pip install -r requirements.txt")
        print("3. Install Node.js dependencies: cd frontend && npm install")
        print("4. Run: ./start.sh")

if __name__ == "__main__":
    main()
