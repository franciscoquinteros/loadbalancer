# Balance Loader Bot

A Telegram bot that automates user creation and balance assignment on a private platform using browser automation.

## Features

### User Creation Flow

1. An operator sends a username to the Telegram bot
2. The bot logs into the platform using admin credentials
3. Creates a new user with the provided username and a fixed password (cocos2025)
4. Sends a confirmation message back on Telegram with the new user credentials

### Balance Assignment Flow

1. The operator replies to the user creation message with "load X pesos"
2. The bot detects which user is being referenced
3. Logs into the platform and searches for the user
4. Assigns the requested amount to the user's account
5. Confirms the action back via Telegram

## Setup

### Prerequisites

- Python 3.8 or higher
- A Telegram Bot Token (get one from [@BotFather](https://t.me/BotFather))
- Admin credentials for the platform

### Installation

1. Clone this repository:

   ```
   git clone https://github.com/yourusername/balanceloader.git
   cd balanceloader
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Install Playwright browsers:

   ```
   playwright install
   ```

4. Configure environment variables:
   - Copy the `.env.example` file to `.env`
   - Fill in your Telegram Bot Token and platform credentials

### Running the Bot

```
python -m bot.main
```

### Deployment

For production deployment on a VPS or server:

1. See the `DEPLOYMENT_GUIDE.md` for detailed instructions on setting up the bot on a Hostinger VPS
2. Use the provided `deploy.sh` script for automated deployment:

   ```
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. For updating an existing installation, use the `update.sh` script:

   ```
   chmod +x update.sh
   ./update.sh
   ```

4. The `balanceloader.service` file is provided as a template for setting up the bot as a systemd service

## Usage

1. Start a conversation with your bot on Telegram
2. To create a user, simply send a username (e.g., "juanperez98")
3. To load balance, reply to the user creation message with "load X pesos" (e.g., "load 2000 pesos")

## Customization

You may need to adjust the selectors in the `browser_automation.py` file to match the actual HTML structure of your platform.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
