# Troubleshooting Guide for VPS Deployment

This guide addresses common issues that may arise when deploying the Balance Loader Bot on a VPS.

## Table of Contents

1. [Connection Issues](#connection-issues)
2. [Browser Automation Problems](#browser-automation-problems)
3. [Service Management](#service-management)
4. [Permission Issues](#permission-issues)
5. [Environment Variables](#environment-variables)

## Connection Issues

### Bot Cannot Connect to Telegram API

**Symptoms:** The bot starts but doesn't respond to messages, or logs show connection errors.

**Solutions:**

1. Verify your internet connection on the VPS:
   ```bash
   ping api.telegram.org
   ```

2. Check if your Telegram Bot Token is correct in the `.env` file.

3. Ensure there are no firewall rules blocking outgoing connections:
   ```bash
   sudo ufw status
   ```

### Cannot Connect to Platform

**Symptoms:** Bot responds to messages but fails when trying to create users or load balance.

**Solutions:**

1. Verify platform URLs in the `.env` file.

2. Check if the platform is accessible from the VPS:
   ```bash
   curl -I your_platform_url
   ```

3. If the platform has IP restrictions, ensure your VPS IP is whitelisted.

## Browser Automation Problems

### Playwright Browser Crashes

**Symptoms:** Logs show browser launch failures or crashes during automation.

**Solutions:**

1. Ensure all Playwright dependencies are installed:
   ```bash
   sudo apt install -y libwoff1 libopus0 libwebp6 libwebpdemux2 libenchant1c2a libgudev-1.0-0 libsecret-1-0 libhyphen0 libgdk-pixbuf2.0-0 libegl1 libnotify4 libxslt1.1 libevent-2.1-7 libgles2 libvpx6 libxcomposite1 libatk1.0-0 libatk-bridge2.0-0 libepoxy0 libgtk-3-0 libharfbuzz-icu0 libxshmfence1
   ```

2. Use Xvfb for headless browser support:
   ```bash
   sudo apt install -y xvfb
   ```

   Update your service file:
   ```ini
   ExecStart=/usr/bin/xvfb-run /opt/balanceloader/venv/bin/python -m bot.main
   ```

3. Check browser logs for specific errors:
   ```bash
   journalctl -u balanceloader.service | grep -i playwright
   ```

### Selectors Not Working

**Symptoms:** The bot fails to find elements on the platform pages.

**Solutions:**

1. The platform's HTML structure may have changed. Update the selectors in `browser_automation.py`.

2. Add debug logging to see what's happening:
   ```python
   # Add to browser_automation.py
   await page.screenshot(path='debug_screenshot.png')
   logger.debug(await page.content())
   ```

3. Increase wait times for slow-loading elements:
   ```python
   await page.wait_for_selector('selector', timeout=30000)  # 30 seconds
   ```

## Service Management

### Service Fails to Start

**Symptoms:** `systemctl status balanceloader.service` shows failed status.

**Solutions:**

1. Check logs for specific errors:
   ```bash
   journalctl -u balanceloader.service -n 50
   ```

2. Verify the paths in the service file are correct:
   ```bash
   cat /etc/systemd/system/balanceloader.service
   ```

3. Ensure the Python executable path is correct:
   ```bash
   ls -la /opt/balanceloader/venv/bin/python
   ```

### Service Starts but Exits Immediately

**Solutions:**

1. Check for missing dependencies or configuration errors in the logs.

2. Try running the bot manually to see errors:
   ```bash
   cd /opt/balanceloader
   source venv/bin/activate
   python -m bot.main
   ```

3. Add the `Restart=on-failure` directive to your service file if not already present.

## Permission Issues

### File Permission Errors

**Symptoms:** Logs show "Permission denied" errors.

**Solutions:**

1. Check ownership of project files:
   ```bash
   ls -la /opt/balanceloader
   ```

2. Fix permissions if needed:
   ```bash
   sudo chown -R your-username:your-username /opt/balanceloader
   chmod +x /opt/balanceloader/bot/main.py
   ```

3. Check if the service user has access to the `.env` file:
   ```bash
   sudo -u your-username cat /opt/balanceloader/.env
   ```

## Environment Variables

### Environment Variables Not Loading

**Symptoms:** Bot fails with errors about missing configuration.

**Solutions:**

1. Verify the `.env` file exists and has correct permissions:
   ```bash
   ls -la /opt/balanceloader/.env
   ```

2. Check if the file contains the required variables:
   ```bash
   grep -v '^#' /opt/balanceloader/.env | grep -v '^$'
   ```

3. Try setting environment variables directly in the service file:
   ```ini
   [Service]
   Environment=TELEGRAM_BOT_TOKEN=your_token_here
   Environment=ADMIN_USERNAME=your_username_here
   # Add other variables as needed
   ```

---

If you continue to experience issues after trying these solutions, please check the logs for specific error messages and consult the project documentation or support channels.