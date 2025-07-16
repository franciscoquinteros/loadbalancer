#!/bin/bash

# Balance Loader Bot Deployment Script
# This script automates the deployment of the Balance Loader Bot on a Linux server

set -e  # Exit on error

echo "===== Balance Loader Bot Deployment ====="
echo ""

# Check if running as root or with sudo
if [ "$(id -u)" -eq 0 ]; then
    echo "This script should not be run as root or with sudo."
    echo "It will use sudo only for commands that require elevated privileges."
    exit 1
fi

# Get the username for the service file
USERNAME=$(whoami)
echo "Deploying as user: $USERNAME"

# Update system and install dependencies
echo "\n[1/7] Updating system and installing dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

# Install Playwright dependencies
echo "\n[2/7] Installing Playwright dependencies..."
sudo apt install -y libwoff1 libopus0 libwebp6 libwebpdemux2 libenchant1c2a libgudev-1.0-0 libsecret-1-0 libhyphen0 libgdk-pixbuf2.0-0 libegl1 libnotify4 libxslt1.1 libevent-2.1-7 libgles2 libvpx6 libxcomposite1 libatk1.0-0 libatk-bridge2.0-0 libepoxy0 libgtk-3-0 libharfbuzz-icu0 libxshmfence1 xvfb

# Create project directory
echo "\n[3/7] Setting up project directory..."
PROJECT_DIR="/opt/balanceloader"

if [ ! -d "$PROJECT_DIR" ]; then
    sudo mkdir -p "$PROJECT_DIR"
    sudo chown "$USERNAME:$USERNAME" "$PROJECT_DIR"
fi

# Copy current directory contents to project directory if not already there
if [ "$(pwd)" != "$PROJECT_DIR" ]; then
    echo "Copying project files to $PROJECT_DIR..."
    rsync -av --exclude 'venv' --exclude '__pycache__' --exclude '.git' ./ "$PROJECT_DIR/"
    cd "$PROJECT_DIR"
fi

# Set up virtual environment
echo "\n[4/7] Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Install Python dependencies
echo "\n[5/7] Installing Python dependencies..."
pip install -r requirements.txt

# Install Playwright browser
echo "\n[6/7] Installing Playwright browser..."
python -m playwright install chromium

# Check and configure .env file
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "\nCreating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit the .env file with your actual credentials:"
    echo "nano $PROJECT_DIR/.env"
fi

# Create and enable systemd service
echo "\n[7/7] Setting up systemd service..."
SERVICE_FILE="/etc/systemd/system/balanceloader.service"

# Create service file from template if it exists, otherwise create it from scratch
if [ -f "balanceloader.service" ]; then
    # Replace placeholder with actual username
    sed "s/your-username/$USERNAME/g" balanceloader.service | sudo tee "$SERVICE_FILE" > /dev/null
else
    echo "Creating service file from scratch..."
    cat << EOF | sudo tee "$SERVICE_FILE" > /dev/null
[Unit]
Description=Balance Loader Telegram Bot
After=network.target

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python -m bot.main
Restart=on-failure
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
fi

# Make scripts executable
chmod +x "$PROJECT_DIR/bot/main.py"

# Reload systemd, enable and start service
sudo systemctl daemon-reload
sudo systemctl enable balanceloader.service

echo "\n===== Deployment Complete! ====="
echo ""
echo "The Balance Loader Bot has been deployed successfully."
echo ""
echo "To start the service:"
echo "  sudo systemctl start balanceloader.service"
echo ""
echo "To check status:"
echo "  sudo systemctl status balanceloader.service"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u balanceloader.service -f"
echo ""
echo "Don't forget to edit your .env file if you haven't already!"
echo "  nano $PROJECT_DIR/.env"
echo ""