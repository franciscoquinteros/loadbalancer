# Balance Loader Bot

A high-speed Telegram bot that automates user creation and balance assignment on a private platform using optimized browser automation.

## Features

### User Creation Flow

1. An operator sends a username to the Telegram bot (e.g., `juanperez98`)
2. The bot automatically creates a new user with the provided username and password `cocos`
3. Sends a Spanish confirmation message that can be easily copied and pasted

### Balance Assignment Flow

1. The operator sends a message with format: `username amount` (e.g., `juanperez98 2000`)
2. The bot detects the username and amount
3. Logs into the platform and searches for the user
4. Assigns the requested amount to the user's account
5. Confirms the action back via Telegram

## Setup

### Prerequisites

- Python 3.8 or higher
- A Telegram Bot Token (get one from [@BotFather](https://t.me/BotFather))
- Admin credentials for the platform
- Platform URLs for login, user creation, and balance management

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

### Creating Users

Send a username to the bot:

```
juanperez98
```

The bot will create the user and respond with:

```
Tu usuario ha sido creado 🍀

———

🔑Usuario: juanperez98
🔒Contraseña: cocos

Enlace: https://cocosbet.com

Avisame cuando quieras cargar y te paso el CVU 💫

❗️ VA TODO EN MINÚSCULAS, INCLUYENDO LAS PRIMERAS LETRAS ❗️

———
```

### Charging Balance

Send a message with format `username amount`:

```
juanperez98 2000
```

This will charge 2000 pesos to the user `juanperez98`.

## Performance

The bot is optimized for speed with:

- Reduced wait times between operations
- Optimized browser settings
- Persistent browser sessions
- Streamlined automation workflows

Target performance: 5x faster than human operators

## Rules

- All usernames must be lowercase with only letters, numbers, and underscores
- All users get the password: `cocos`
- No confirmation dialogs - operations execute immediately
- Simple format: `username` for creation, `username amount` for charging
