# Balance Loader Bot

A high-speed automation system that provides user creation and balance assignment on a private platform using optimized browser automation. Available as both a Telegram bot and HTTP API for integration with external systems like Kommo CRM.

## Features

### Available Interfaces

- **Telegram Bot**: Interactive bot for manual operations
- **HTTP API**: RESTful API for integration with external systems (Kommo CRM)

### User Creation Flow

#### Via Telegram Bot:

1. An operator sends a username to the Telegram bot (e.g., `juanperez98`)
2. The bot automatically creates a new user with the provided username and password `cocos1`
3. Sends a Spanish confirmation message that can be easily copied and pasted

#### Via HTTP API:

1. External system sends POST request to `/api/create-user` endpoint
2. Returns structured response with success/conflict/error status
3. Handles username collisions automatically

### Balance Assignment Flow (Telegram Bot Only)

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

### Running the Telegram Bot

```bash
# Run directly
python -m bot.main

# Or as systemd service
sudo systemctl start balanceloader.service
```

### Running the HTTP API Server

```bash
# Run directly
python run_api.py

# Or as systemd service
sudo cp rpa-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rpa-api.service
sudo systemctl start rpa-api.service
```

The API server runs on `http://127.0.0.1:8001` by default.

### Creating Users

#### Via Telegram Bot

Send a username to the bot:

```
juanperez98
```

The bot will create the user and respond with:

```
Tu usuario ha sido creado 🍀

———

🔑Usuario: juanperez98
🔒Contraseña: cocos1

Enlace: https://cocosbet.com

Avisame cuando quieras cargar y te paso el CVU 💫

❗️ VA TODO EN MINÚSCULAS, INCLUYENDO LAS PRIMERAS LETRAS ❗️

———
```

#### Via HTTP API

```bash
curl -X POST http://127.0.0.1:8001/api/create-user \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test123",
    "captured_user_name": "Juan",
    "candidate_username": "juanperez98",
    "attempt_number": 1
  }'
```

Response:

```json
{
  "status": "success",
  "generated_username": "juanperez98",
  "response_message": "Usuario juanperez98 creado exitosamente. Contraseña: cocos1"
}
```

### Charging Balance (Telegram Bot Only)

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
- All users get the password: `cocos1`
- No confirmation dialogs - operations execute immediately
- Simple format: `username` for creation, `username amount` for charging

## API Integration

### For Kommo CRM Integration

The HTTP API is designed to integrate with external systems like Kommo CRM. See the following documentation:

- **[RPA_INTEGRATION.md](RPA_INTEGRATION.md)** - Complete integration guide with Kommo CRM
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Detailed API documentation
- **[GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md)** - Google Sheets logging setup

### Testing the API

Test the API server:

```bash
python test_api.py
```

### Health Check

```bash
curl http://127.0.0.1:8001/health
```
