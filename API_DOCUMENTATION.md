# RPA Balance Loader API Documentation

This document describes the HTTP API wrapper for the RPA Balance Loader bot, designed for integration with the Kommo CRM system.

## Overview

The RPA API provides HTTP endpoints to access the browser automation functionality that was previously only available through the Telegram bot interface. This allows external systems (like the Kommo bot) to create users programmatically.

## Architecture

```
┌─────────────┐    HTTP API    ┌─────────────┐    Browser     ┌─────────────┐
│   Kommo     │──────────────→ │    RPA      │──────────────→ │   Target    │
│    Bot      │                │    API      │   Automation   │  Platform   │
└─────────────┘                └─────────────┘                └─────────────┘
                                       │
                                       ↓
                               ┌─────────────┐
                               │   Google    │
                               │   Sheets    │
                               │   Logging   │
                               └─────────────┘
```

## Setup and Installation

### 1. Install Dependencies

```bash
cd /opt/balanceloader
pip install -r requirements.txt
```

### 2. Configure Environment Variables

The API server uses the same environment variables as the Telegram bot:

```bash
# Browser automation credentials
ADMIN_LOGIN_URL=https://your-platform.com/login
CREATE_USER_URL=https://your-platform.com/admin/create-user
BALANCE_URL=https://your-platform.com/admin/balance
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_admin_password

# Google Sheets logging
GOOGLE_SHEETS_ID=your_google_sheets_id
GOOGLE_CREDENTIALS_PATH=path_to_service_account_json

# API server configuration (optional)
RPA_API_HOST=127.0.0.1
RPA_API_PORT=8001
RPA_BOT_API_KEY=optional_api_key_for_security
```

### 3. Run the API Server

#### Option A: Direct Python execution

```bash
cd /opt/balanceloader
python run_api.py
```

#### Option B: Using systemd service

```bash
# Copy service file
sudo cp rpa-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rpa-api.service
sudo systemctl start rpa-api.service

# Check status
sudo systemctl status rpa-api.service
```

## API Endpoints

### POST /api/create-user

Creates a new user account via browser automation.

**Request Body:**

```json
{
  "conversation_id": "12345",
  "captured_user_name": "Sofia",
  "candidate_username": "sofia1234",
  "attempt_number": 1
}
```

**Request Fields:**

- `conversation_id` (string): Unique identifier for the conversation/request
- `captured_user_name` (string): Original user name extracted from conversation
- `candidate_username` (string): Username to attempt to create
- `attempt_number` (integer): Attempt number for collision handling

**Response - Success:**

```json
{
  "status": "success",
  "generated_username": "sofia1234",
  "response_message": "Usuario sofia1234 creado exitosamente. Contraseña: cocos",
  "error_detail": null
}
```

**Response - Username Conflict:**

```json
{
  "status": "conflict",
  "generated_username": null,
  "response_message": "Username already exists",
  "error_detail": "User sofia1234 already exists in the system"
}
```

**Response - System Error:**

```json
{
  "status": "error",
  "generated_username": null,
  "response_message": "User creation failed",
  "error_detail": "Database connection timeout"
}
```

### GET /health

Health check endpoint for monitoring.

**Response:**

```json
{
  "status": "healthy",
  "service": "RPA Bot API",
  "timestamp": "2024-01-15T10:30:00.123456"
}
```

### GET /

Root endpoint with service information.

**Response:**

```json
{
  "service": "RPA Balance Loader API",
  "status": "running",
  "version": "1.0.0",
  "endpoints": {
    "create_user": "/api/create-user",
    "health": "/health"
  }
}
```

## Integration with Kommo Bot

The Kommo bot should call this API as described in the RPA_INTEGRATION.md document:

```python
import requests

# Example request to create user
response = requests.post("http://localhost:8001/api/create-user", json={
    "conversation_id": "conv_123",
    "captured_user_name": "Sofia",
    "candidate_username": "sofia1234",
    "attempt_number": 1
})

result = response.json()

if result["status"] == "success":
    print(f"User created: {result['generated_username']}")
elif result["status"] == "conflict":
    print("Username exists, try different suffix")
elif result["status"] == "error":
    print(f"Error: {result['error_detail']}")
```

## Error Handling and Collision Detection

### Username Conflicts

When a username already exists, the API returns `status: "conflict"`. The Kommo bot should:

1. Generate a new username with different random digits
2. Retry the API call with the new username
3. Repeat until success or maximum attempts reached

### System Errors

When browser automation fails due to system issues, the API returns `status: "error"`. Common causes:

- Network connectivity issues
- Platform login failures
- Browser automation timeouts
- Platform UI changes

## Logging and Monitoring

### Google Sheets Integration

All successful user creations are automatically logged to Google Sheets with:

- Username created
- Timestamp
- Operator (kommo*bot*{conversation_id})

### Health Monitoring

Monitor the API server using the `/health` endpoint:

```bash
# Check API health
curl http://localhost:8001/health

# Expected response
{
    "status": "healthy",
    "service": "RPA Bot API",
    "timestamp": "2024-01-15T10:30:00.123456"
}
```

### Service Logs

View API server logs:

```bash
# For systemd service
sudo journalctl -u rpa-api.service -f

# For direct execution
# Logs will appear in terminal output
```

## Security Considerations

### Network Security

- API server runs on localhost only (127.0.0.1:8001)
- No external network access by default
- Communication with Kommo bot via internal network only

### Authentication

- Optional API key support via `RPA_BOT_API_KEY` environment variable
- CORS configured for localhost communication only

### Browser Security

- Headless browser automation
- Secure credential handling from environment variables
- Browser context isolation

## Troubleshooting

### API Server Won't Start

1. Check port availability:

```bash
netstat -tlnp | grep 8001
```

2. Check environment variables:

```bash
python -c "import os; print('LOGIN_URL:', os.getenv('ADMIN_LOGIN_URL'))"
```

3. Check dependencies:

```bash
pip list | grep -E "(fastapi|uvicorn)"
```

### User Creation Fails

1. Test browser automation directly:

```bash
cd /opt/balanceloader
python -c "
from bot.browser_automation import create_user
import asyncio
result = asyncio.run(create_user('testuser123', 'cocos'))
print(result)
"
```

2. Check platform access:

```bash
curl -I https://your-platform.com
```

3. Verify login credentials in environment variables

### API Connection Issues

1. Test API connectivity:

```bash
curl http://localhost:8001/health
```

2. Check CORS configuration if calling from browser
3. Verify request format matches API specification

## Performance Considerations

### Concurrent Requests

- Browser automation is single-threaded by design
- API handles one user creation at a time
- Multiple requests are queued automatically

### Resource Management

- Browser context is reused across requests
- Automatic cleanup on service restart
- Memory usage monitoring recommended

### Response Times

- Typical user creation: 3-8 seconds
- Health check: <100ms
- Timeout configured at 30 seconds

## API Version History

### v1.0.0 (Current)

- Initial API implementation
- POST /api/create-user endpoint
- GET /health endpoint
- Google Sheets logging integration
- Systemd service support

## Support

For issues and questions:

1. Check service logs: `sudo journalctl -u rpa-api.service`
2. Verify environment configuration
3. Test browser automation independently
4. Review RPA_INTEGRATION.md for integration details
