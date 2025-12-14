# Email Agent

A Flask server for Gmail actions using Composio with OAuth2 authentication. Designed to be packaged as a standalone .exe file with local credential storage.

## Features

- **OAuth2 Authentication**: Secure Gmail authentication using Google OAuth2
- **Natural Language Queries**: Execute Gmail actions using natural language prompts
- **Local Credential Storage**: Credentials stored locally for .exe deployment
- **RESTful API**: Clean API endpoints for all Gmail operations

## Prerequisites

1. **Composio Account**: Get your API key from [Composio Dashboard](https://app.composio.dev)
2. **OpenAI Account**: Get your API key from [OpenAI Platform](https://platform.openai.com)
3. **Google Cloud Console**: Create OAuth2 credentials for Gmail API

### Setting up Google OAuth2 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Gmail API" and enable it
4. Create OAuth2 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Web application"
   - Add authorized redirect URI: `https://backend.composio.dev/api/v1/auth-apps/add`
   - Save the **Client ID** and **Client Secret**

## Installation

### Using pip

```bash
pip install -e .
```

### Using uv (recommended)

```bash
uv sync
```

## Configuration

### Option 1: Environment Variables

```bash
export COMPOSIO_API_KEY="your_composio_api_key"
export OPENAI_API_KEY="your_openai_api_key"
export GMAIL_CLIENT_ID="your_gmail_client_id"
export GMAIL_CLIENT_SECRET="your_gmail_client_secret"
```

### Option 2: API Configuration

Start the server and configure via API:

```bash
curl -X POST http://localhost:5000/config \
  -H "Content-Type: application/json" \
  -d '{
    "composio_api_key": "your_composio_api_key",
    "openai_api_key": "your_openai_api_key",
    "gmail_client_id": "your_gmail_client_id",
    "gmail_client_secret": "your_gmail_client_secret",
    "user_id": "your_user_id"
  }'
```

### Option 3: Create credentials.json

Create a `credentials.json` file in the same directory:

```json
{
  "composio_api_key": "your_composio_api_key",
  "openai_api_key": "your_openai_api_key",
  "gmail_client_id": "your_gmail_client_id",
  "gmail_client_secret": "your_gmail_client_secret",
  "user_id": "default_user"
}
```

## Running the Server

```bash
# Using Python directly
python main.py

# Using the installed script
email-agent

# Using uv
uv run python main.py
```

On first run, if credentials are configured, you'll be prompted to authenticate Gmail. A browser window will open for OAuth2 authentication.

## API Endpoints

### Status & Configuration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API documentation |
| `/status` | GET | Check authentication status |
| `/config` | GET | View current configuration (masked) |
| `/config` | POST | Update configuration |
| `/authenticate` | POST | Initiate Gmail authentication |
| `/logout` | POST | Clear authentication |

### Gmail Actions

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/query` | POST | Execute Gmail action with natural language |
| `/send` | POST | Send an email |
| `/draft` | POST | Create an email draft |
| `/emails` | GET | Fetch recent emails |
| `/drafts` | GET | List email drafts |
| `/labels` | GET | List Gmail labels |

## API Examples

### Check Status

```bash
curl http://localhost:5000/status
```

### Authenticate Gmail

```bash
curl -X POST http://localhost:5000/authenticate
```

### Send an Email

```bash
curl -X POST http://localhost:5000/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": "recipient@example.com",
    "subject": "Hello from Email Agent",
    "body": "This email was sent using the Email Agent API!"
  }'
```

### Create a Draft

```bash
curl -X POST http://localhost:5000/draft \
  -H "Content-Type: application/json" \
  -d '{
    "to": "recipient@example.com",
    "subject": "Draft Email",
    "body": "This is a draft email."
  }'
```

### Natural Language Query

```bash
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me my last 5 unread emails"}'
```

```bash
curl -X POST http://localhost:5000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Reply to the last email from john@example.com saying thank you for the update"}'
```

### Fetch Emails

```bash
# Fetch 10 emails from inbox (default)
curl http://localhost:5000/emails

# Fetch 5 emails from a specific label
curl "http://localhost:5000/emails?max=5&label=IMPORTANT"
```

### List Labels

```bash
curl http://localhost:5000/labels
```

## Building as .exe

To package as a standalone executable:

```bash
# Install PyInstaller
pip install pyinstaller

# Build the executable
pyinstaller --onefile --name EmailAgent main.py
```

The executable will be created in the `dist/` directory. Copy `credentials.json` to the same directory as the .exe if pre-configuring credentials.

## File Structure

```
email-agent/
├── main.py              # Flask server and Gmail agent
├── config.py            # Configuration management
├── credentials.json     # Stored credentials (auto-generated)
├── auth_config.json     # OAuth tokens (auto-generated)
├── pyproject.toml       # Project dependencies
└── README.md            # This file
```

## Supported Gmail Actions

- **GMAIL_FETCH_EMAILS**: Fetch emails from inbox
- **GMAIL_SEND_EMAIL**: Send an email
- **GMAIL_CREATE_EMAIL_DRAFT**: Create a draft
- **GMAIL_LIST_DRAFTS**: List all drafts
- **GMAIL_SEND_DRAFT**: Send an existing draft
- **GMAIL_DELETE_DRAFT**: Delete a draft
- **GMAIL_REPLY_TO_THREAD**: Reply to an email thread
- **GMAIL_GET_THREAD**: Get email thread details
- **GMAIL_LIST_THREADS**: List email threads
- **GMAIL_ADD_LABEL_TO_EMAIL**: Add label to email
- **GMAIL_REMOVE_LABEL_FROM_EMAIL**: Remove label from email
- **GMAIL_LIST_LABELS**: List all labels
- **GMAIL_CREATE_LABEL**: Create a new label

## Troubleshooting

### "Missing credentials" error
Ensure all required credentials are set either via environment variables, API, or credentials.json.

### OAuth2 authentication fails
1. Verify your Google OAuth2 credentials are correct
2. Ensure the redirect URI is set to `https://backend.composio.dev/api/v1/auth-apps/add`
3. Check that Gmail API is enabled in your Google Cloud project

### "Gmail not authenticated" error
Run the authentication flow via POST `/authenticate` or restart the server and authenticate when prompted.

## License

MIT License

