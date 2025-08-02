# Deployment Guide: Balance Loader Bot on Hostinger VPS

This guide provides step-by-step instructions for deploying the Balance Loader Bot on a Hostinger VPS and setting it up as a systemd service for continuous operation.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [VPS Setup](#vps-setup)
3. [Project Installation](#project-installation)
4. [Environment Configuration](#environment-configuration)
5. [Playwright Setup](#playwright-setup)
6. [Creating a Systemd Service](#creating-a-systemd-service)
7. [Starting and Managing the Service](#starting-and-managing-the-service)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

Before you begin, make sure you have:

- A Hostinger VPS account with SSH access
- A Telegram bot token (obtained from [@BotFather](https://t.me/botfather))
- Admin credentials for the platform
- Platform URLs for login, user creation, and balance management

## VPS Setup

### 1. Connect to Your VPS

```bash
ssh username@your-vps-ip
```

Replace `username` and `your-vps-ip` with your actual VPS credentials.

### 2. Update System Packages

```bash
sudo apt update
sudo apt upgrade -y
```

### 3. Install Required System Dependencies

```bash
sudo apt install -y python3 python3-pip python3-venv git
```

### 4. Install Playwright Dependencies

Playwright requires additional system dependencies for browser automation:

```bash
sudo apt install -y libwoff1 libopus0 libwebp6 libwebpdemux2 libenchant1c2a libgudev-1.0-0 libsecret-1-0 libhyphen0 libgdk-pixbuf2.0-0 libegl1 libnotify4 libxslt1.1 libevent-2.1-7 libgles2 libvpx6 libxcomposite1 libatk1.0-0 libatk-bridge2.0-0 libepoxy0 libgtk-3-0 libharfbuzz-icu0 libxshmfence1
```

## Project Installation

### 1. Create a Directory for the Project

```bash
mkdir -p /opt/balanceloader
cd /opt/balanceloader
```

### 2. Clone the Repository (or Upload Files)

Option 1: If your project is in a Git repository:

```bash
git clone https://your-repository-url.git .
```

Option 2: If you're uploading files manually, use SCP or SFTP:

```bash
# From your local machine
scp -r /path/to/local/balanceloader/* username@your-vps-ip:/opt/balanceloader/
```

### 3. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

## Environment Configuration

### 1. Create and Configure .env File

```bash
cp .env.example .env
nano .env
```

Update the following variables with your actual values:

```
# Telegram Bot Token
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Platform Credentials
ADMIN_USERNAME=your_admin_username_here
ADMIN_PASSWORD=your_admin_password_here

# Platform URLs
ADMIN_LOGIN_URL=https://platform-url.com/login
CREATE_USER_URL=https://platform-url.com/create-user
BALANCE_URL=https://platform-url.com/balance
```

Save and exit (Ctrl+X, then Y, then Enter).

## Playwright Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
python -m playwright install chromium
```

### 3. Test the Installation

```bash
python -m bot.main
```

Press Ctrl+C to stop the bot after confirming it works.

## Creating a Systemd Service

### 1. Create a Service File

```bash
sudo nano /etc/systemd/system/balanceloader.service
```

Add the following content:

```ini
[Unit]
Description=Balance Loader Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/balancebot/balanceloader
ExecStart=/home/balancebot/balanceloader/venv/bin/python bot/main.py
Restart=on-failure
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Replace `your-username` with your VPS username.

### 2. Reload Systemd

```bash
sudo systemctl daemon-reload
```

## Starting and Managing the Service

### 1. Enable the Service

This ensures the bot starts automatically on system boot:

```bash
sudo systemctl enable balanceloader.service
```

### 2. Start the Service

```bash
sudo systemctl start balanceloader.service
```

### 3. Check Service Status

```bash
sudo systemctl status balanceloader.service
```

### 4. View Logs

```bash
sudo journalctl -u balanceloader.service -f
```

Press Ctrl+C to stop viewing logs.

### 5. Restart the Service

After making changes to the bot code or configuration:

```bash
sudo systemctl restart balanceloader.service
```

### 6. Stop the Service

```bash
sudo systemctl stop balanceloader.service
```

## Troubleshooting

### Headless Browser Issues

If you encounter issues with Playwright's headless browser:

1. Ensure all Playwright dependencies are installed
2. Check that the `headless` parameter in `browser_automation.py` is set to `True`
3. Try running with xvfb if needed:

```bash
sudo apt install -y xvfb
```

And update your service file:

```ini
ExecStart=/usr/bin/xvfb-run /opt/balanceloader/venv/bin/python -m bot.main
```

### Permission Issues

If you encounter permission issues:

```bash
sudo chown -R your-username:your-username /opt/balanceloader
chmod +x /opt/balanceloader/bot/main.py
```

### Connection Timeouts

If the bot experiences connection timeouts to the platform:

1. Check your network configuration
2. Increase timeout values in the Playwright code
3. Ensure the platform URLs are correct and accessible from the VPS

---

For additional support or questions, please refer to the project documentation or contact the development team.
