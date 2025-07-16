#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.8 or higher"""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required.")
        sys.exit(1)
    print("✓ Python version check passed.")

def check_env_file():
    """Check if .env file exists, create from example if not"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        print(".env file not found. Creating from .env.example...")
        with open(env_example, "r") as example:
            with open(env_file, "w") as env:
                env.write(example.read())
        print("✓ Created .env file. Please edit it with your actual credentials.")
    elif env_file.exists():
        print("✓ .env file exists.")
    else:
        print("Error: Neither .env nor .env.example file found.")
        sys.exit(1)

def install_dependencies():
    """Install Python dependencies"""
    print("Installing Python dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("✓ Dependencies installed.")

def install_playwright_browsers():
    """Install Playwright browsers"""
    print("Installing Playwright browsers...")
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
    print("✓ Playwright browsers installed.")

def main():
    """Run setup steps"""
    print("Setting up Balance Loader Bot...\n")
    
    check_python_version()
    install_dependencies()
    install_playwright_browsers()
    check_env_file()
    
    print("\nSetup complete! You can now run the bot with:")
    print("python -m bot.main")

if __name__ == "__main__":
    main()