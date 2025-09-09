# RPA Bot Integration Guide

This document explains how the Kommo CRM Messaging Agent integrates with the RPA Balance Loader Bot for user creation.

## System Architecture

### High-Level Overview

```
┌─────────────┐    Webhooks    ┌─────────────┐    HTTP API    ┌─────────────┐    Browser     ┌─────────────┐
│   Kommo     │──────────────→ │   Kommo     │──────────────→ │    RPA      │──────────────→ │   Target    │
│    CRM      │                │    Bot      │                │    Bot      │   Automation   │  Platform   │
└─────────────┘                └─────────────┘                └─────────────┘                └─────────────┘
      │                              │                              │                              │
      │                              ↓                              ↓                              │
      │                      ┌─────────────┐                ┌─────────────┐                      │
      │                      │   Google    │                │   Google    │                      │
      └──────────────────────│   Sheets    │                │   Sheets    │──────────────────────┘
                             │  (Kommo)    │                │   (RPA)     │
                             └─────────────┘                └─────────────┘
```

## Component Responsibilities

### Kommo Bot (kommobot/)

- **Primary Role**: Conversation orchestration and flow management
- **Responsibilities**:
  - Process incoming Kommo webhooks
  - Manage conversation state and user interactions
  - Extract and clean user names from messages
  - Generate username candidates with random digits
  - Call RPA bot for user creation
  - Handle collision detection and retries
  - Update Kommo CRM fields and tags
  - Provide AI-powered responses to common questions
  - Log all events to Google Sheets

### RPA Bot (balanceloader/)

- **Primary Role**: User creation on target platform via browser automation
- **Responsibilities**:
  - Receive HTTP API requests for user creation
  - Use Playwright browser automation to navigate target platform
  - Perform actual user registration with provided credentials
  - Detect username conflicts and report status
  - Return success/failure status with detailed messages
  - Log RPA operations to Google Sheets

## Integration Flow

### 1. Conversation Initiation

```
User Message → Kommo CRM → Webhook → Kommo Bot
```

The flow starts when a user sends their first message in Kommo CRM:

1. **Kommo CRM** receives user message
2. **Kommo CRM** sends webhook to Kommo Bot
3. **Kommo Bot** processes webhook and starts conversation flow

### 2. Conversation Flow Execution

```
Greeting → Informational → Name Capture → Username Generation
```

**Step 1: Greeting**

- Kommo Bot sends random greeting template
- Marks step as completed in conversation state

**Step 2: Informational**

- Sends terms & conditions with name request
- Uses random template from Google Sheets
- Waits for user response

**Step 3: Name Capture**

- Extracts usable name from user message
- Validates name is not ambiguous
- Stores extracted name in conversation state

**Step 4: Username Generation**

- Cleans extracted name (removes emojis, spaces, special chars)
- Generates candidate username: `{clean_name}{4_random_digits}`
- Initiates RPA bot integration

### 3. RPA Bot Integration Sequence

#### Step 3.1: Username Creation Request

```python
# Request sent from Kommo Bot to RPA Bot
POST http://localhost:8001/api/create-user
{
    "conversation_id": "12345",
    "captured_user_name": "Sofia",
    "candidate_username": "sofia1234",
    "attempt_number": 1
}
```

#### Step 3.2: RPA Bot Processing

```
RPA Bot → Browser Automation → Target Platform
```

1. **RPA Bot** receives HTTP request
2. **Browser Automation** launches headless Chrome
3. **Platform Login** using admin credentials
4. **Navigate** to user creation form
5. **Fill Form** with username and password ("cocos1")
6. **Submit** form and wait for response
7. **Parse Result** from platform (success/error/conflict)

#### Step 3.3: Response Processing

```python
# Response types from RPA Bot to Kommo Bot

# SUCCESS
{
    "status": "success",
    "generated_username": "sofia1234",
    "response_message": "Usuario sofia1234 creado exitosamente. Contraseña: cocos1"
}

# CONFLICT (username exists)
{
    "status": "conflict",
    "response_message": "Username already exists",
    "error_detail": "User sofia1234 already exists in the system"
}

# ERROR (system error)
{
    "status": "error",
    "response_message": "User creation failed",
    "error_detail": "Database connection timeout"
}
```

### 4. Collision Handling

```
Collision Detected → Generate New Username → Retry RPA Call
```

When RPA Bot returns `status: "conflict"`:

1. **Kommo Bot** generates new 4-digit suffix
2. **New Username**: `sofia5678` (different digits)
3. **Retry Call** to RPA Bot with new candidate
4. **Repeat** until success or max attempts reached (default: 10)

#### Collision Handling Logic

```python
attempts = 0
max_attempts = 10

while attempts < max_attempts:
    attempts += 1
    candidate = f"{clean_name}{random.randint(0000, 9999):04d}"

    success, response, status = await rpa_client.create_user(
        conversation_id=conv_id,
        user_name=extracted_name,
        candidate_username=candidate,
        attempt_number=attempts
    )

    if status == "success":
        return True, candidate, response, attempts
    elif status == "conflict":
        continue  # Try again with new digits
    elif status == "error":
        break  # Stop on system errors

# Max attempts reached
return False, None, "Max attempts exceeded", attempts
```

### 5. Successful Creation Flow

```
RPA Success → Send Response → CBU Messages → Update Kommo
```

When RPA Bot successfully creates user:

1. **Send Success Message** using random template
2. **Send CBU Messages** (account info + CBU number)
3. **Update Kommo Field** ("Username" = generated username)
4. **Add Kommo Tag** ("USUARIO AGENDADO")
5. **Mark Conversation Complete**

### 6. Error Handling

```
RPA Error → Log Error → Manual Takeover Flag
```

When RPA Bot encounters system errors:

1. **Log Error** to Google Sheets
2. **Mark Conversation** for manual takeover
3. **Stop Automation** for this conversation
4. **Human Operator** takes over in Kommo CRM

## Technical Implementation Details

### Kommo Bot Configuration

```python
# kommobot/config.py
RPA_BOT_URL = "http://localhost:8001/api/create-user"
RPA_BOT_API_KEY = "optional_security_key"
MAX_USERNAME_ATTEMPTS = 10
```

### RPA Bot API Wrapper

The existing balanceloader is a Telegram bot. For Kommo integration, we wrap it with an HTTP API:

```python
# balanceloader/api_server.py
from fastapi import FastAPI
from bot.browser_automation import create_user

app = FastAPI()

@app.post("/api/create-user")
async def create_user_endpoint(request: UserCreationRequest):
    success, message = await create_user(
        username=request.candidate_username,
        password="cocos1"  # Fixed password
    )

    if success:
        return {"status": "success", "generated_username": username}
    else:
        # Determine if collision or error
        if "exists" in message.lower():
            return {"status": "conflict", "error_detail": message}
        else:
            return {"status": "error", "error_detail": message}
```

### Network Communication

```bash
# Both services run on same server
Kommo Bot:  localhost:8080  (External via Nginx)
RPA Bot:    localhost:8001  (Internal only)

# Communication flow
Kommo Bot (8080) → HTTP POST → RPA Bot (8001)
```

### Security Considerations

#### 1. Network Security

- RPA Bot API runs on internal port (8001)
- No external access to RPA Bot
- All communication via localhost

#### 2. Authentication

- Optional API key for RPA Bot requests
- Kommo webhook signature verification
- Service account authentication for Google Sheets

#### 3. Error Handling

- Timeout protection on RPA calls
- Retry logic with exponential backoff
- Circuit breaker pattern for RPA failures

## Monitoring and Logging

### Google Sheets Logging

#### Kommo Bot Events

```
Event Log Columns:
- timestamp: ISO 8601 with Argentina timezone
- conversation_id: Kommo conversation ID
- event_type: rpa_request, rpa_response, etc.
- extracted_name: Original user name
- candidate_username: Username being tested
- generated_username: Final successful username
- attempt: Attempt number (1-10)
- status: success/conflict/error
- error_detail: Error description if applicable
```

#### RPA Bot Events

```
RPA Log Columns:
- timestamp: Operation timestamp
- username: Username being created
- operation: create_user, assign_balance
- status: success/failure
- details: Platform response
- operator: Source of request (kommo_bot)
```

### Health Monitoring

#### Kommo Bot Health Check

```bash
curl https://your-domain.com/health
{
    "status": "healthy",
    "components": {
        "rpa": {"status": "ok", "message": "RPA bot responding"},
        "sheets": {"status": "ok", "message": "Connected to sheets"},
        "ai": {"status": "ok", "initialized": true}
    }
}
```

#### RPA Bot Health Check

```bash
curl http://localhost:8001/health
{
    "status": "healthy",
    "service": "RPA Bot API"
}
```

## Deployment Architecture

### Single Server Deployment

```
┌─────────────────────────────────────────────┐
│                 VPS Server                  │
│                                             │
│  ┌─────────────┐    ┌─────────────┐       │
│  │   Nginx     │    │   Kommo     │       │
│  │   :80/443   │────│   Bot       │       │
│  │             │    │   :8080     │       │
│  └─────────────┘    └─────────────┘       │
│                             │              │
│                             │ HTTP         │
│                             ↓              │
│                     ┌─────────────┐       │
│                     │    RPA      │       │
│                     │    Bot      │       │
│                     │   :8001     │       │
│                     └─────────────┘       │
│                                             │
└─────────────────────────────────────────────┘
```

### Service Dependencies

```
nginx.service
├── kommobot.service
    └── rpa-bot.service
```

Both services must be running for full functionality:

- **RPA Bot** must start first (dependency)
- **Kommo Bot** connects to RPA Bot on startup
- **Nginx** proxies external traffic to Kommo Bot

## Testing the Integration

### 1. Unit Testing

```bash
# Test RPA Bot API directly
curl -X POST http://localhost:8001/api/create-user \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "test123",
    "captured_user_name": "Test",
    "candidate_username": "test1234",
    "attempt_number": 1
  }'
```

### 2. Integration Testing

```bash
# Test through Kommo Bot
curl -X POST https://your-domain.com/admin/test-rpa \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "conversation_id": "test456"
  }'
```

### 3. End-to-End Testing

1. Send message to Kommo CRM conversation
2. Monitor Kommo Bot logs
3. Check RPA Bot logs
4. Verify user creation on target platform
5. Confirm Google Sheets logging

## Troubleshooting Common Issues

### 1. RPA Bot Not Responding

```bash
# Check RPA Bot service
sudo systemctl status rpa-bot.service

# Check port availability
netstat -tlnp | grep 8001

# Test RPA Bot health
curl http://localhost:8001/health
```

### 2. Username Collisions

```bash
# Check collision rate in logs
sudo journalctl -u kommobot.service | grep "conflict"

# Review username generation logic
grep -n "generate_username_candidate" /opt/kommobot/username_generator.py
```

### 3. Browser Automation Failures

```bash
# Check browser dependencies
cd /opt/balanceloader
python -m playwright install --with-deps

# Clear browser context
rm -rf /opt/balanceloader/browser_context/
sudo systemctl restart rpa-bot.service
```

### 4. Platform Changes

If the target platform changes its UI:

1. **Update Selectors** in `browser_automation.py`
2. **Test Form Detection** logic
3. **Update Error Handling** for new messages
4. **Restart RPA Bot** service

## Performance Optimization

### 1. Concurrent Operations

- RPA Bot handles one user creation at a time
- Kommo Bot can queue multiple requests
- Database/platform limitations may require throttling

### 2. Retry Strategy

```python
# Exponential backoff for RPA calls
delays = [1, 2, 4, 8, 16]  # seconds
for attempt, delay in enumerate(delays):
    if attempt > 0:
        await asyncio.sleep(delay)
    # Make RPA call
```

### 3. Resource Management

- Browser context reuse in RPA Bot
- Connection pooling for HTTP requests
- Memory cleanup for long-running processes

## Future Enhancements

### 1. Scalability

- Multiple RPA Bot instances for high volume
- Load balancing between RPA instances
- Database-backed state management

### 2. Reliability

- Health checks with automatic restart
- Dead letter queue for failed operations
- Comprehensive monitoring dashboards

### 3. Security

- End-to-end encryption for sensitive data
- API rate limiting and authentication
- Audit logging for compliance

---

This integration provides a robust, scalable solution for automated user creation while maintaining clear separation of concerns between conversation management and browser automation.
