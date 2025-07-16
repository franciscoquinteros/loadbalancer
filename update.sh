#!/bin/bash

# Balance Loader Bot Update Script
# This script updates an existing installation of the Balance Loader Bot

set -e  # Exit on error

echo "===== Balance Loader Bot Update ====="
echo ""

# Check if running as root or with sudo
if [ "$(id -u)" -eq 0 ]; then
    echo "This script should not be run as root or with sudo."
    echo "It will use sudo only for commands that require elevated privileges."
    exit 1
fi

# Define project directory
PROJECT_DIR="/opt/balanceloader"

# Check if project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Project directory $PROJECT_DIR does not exist."
    echo "Please run the deployment script first."
    exit 1
fi

# Navigate to project directory
cd "$PROJECT_DIR"

# Stop the service
echo "\n[1/5] Stopping the service..."
sudo systemctl stop balanceloader.service

# Backup the current .env file
echo "\n[2/5] Backing up configuration..."
if [ -f ".env" ]; then
    cp .env .env.backup
    echo "Backed up .env to .env.backup"
fi

# Update code
echo "\n[3/5] Updating code..."

# If this is a git repository
if [ -d ".git" ]; then
    echo "Updating from git repository..."
    git pull
else
    # If running the update script from a directory with new code
    if [ "$(pwd)" != "$PROJECT_DIR" ]; then
        echo "Copying new files to $PROJECT_DIR..."
        rsync -av --exclude 'venv' --exclude '__pycache__' --exclude '.git' --exclude '.env' ./ "$PROJECT_DIR/"
    else
        echo "Warning: Not a git repository and not running from a source directory."
        echo "Please specify how to update the code."
    fi
fi

# Update dependencies
echo "\n[4/5] Updating dependencies..."
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Update Playwright browsers
python -m playwright install chromium

# Restore .env if needed
if [ -f ".env.backup" ] && [ ! -f ".env" ]; then
    cp .env.backup .env
    echo "Restored .env from backup"
fi

# Make scripts executable
chmod +x "$PROJECT_DIR/bot/main.py"

# Start the service
echo "\n[5/5] Starting the service..."
sudo systemctl start balanceloader.service

# Check service status
echo "\nChecking service status..."
sudo systemctl status balanceloader.service

echo "\n===== Update Complete! ====="
echo ""
echo "The Balance Loader Bot has been updated successfully."
echo ""
echo "To view logs:"
echo "  sudo journalctl -u balanceloader.service -f"
echo ""