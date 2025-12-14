"""
Email Agent - Flask server for Gmail actions using Composio
OAuth2 authentication with credential storage for .exe deployment
"""

import os
import sys
import webbrowser
from typing import Optional
from flask import Flask, request, jsonify

from config import config

# Set environment variables from config before importing Composio
if config.composio_api_key:
    os.environ['COMPOSIO_API_KEY'] = config.composio_api_key
if config.openai_api_key:
    os.environ['OPENAI_API_KEY'] = config.openai_api_key

from composio import Composio
from openai import OpenAI

app = Flask(__name__)

# Global clients
composio_client: Optional[Composio] = None
openai_client: Optional[OpenAI] = None


def initialize_clients():
    """Initialize Composio and OpenAI clients."""
    global composio_client, openai_client
    
    if not config.is_configured():
        missing = config.get_missing_credentials()
        raise ValueError(f"Missing credentials: {', '.join(missing)}")
    
    composio_client = Composio(api_key=config.composio_api_key)
    openai_client = OpenAI(api_key=config.openai_api_key)


def check_connected_account_exists() -> bool:
    """Check if an active Gmail connection exists for the user."""
    if not composio_client:
        return False
    
    try:
        connected_accounts = composio_client.connected_accounts.list(
            user_ids=[config.user_id],
            toolkit_slugs=["GMAIL"],
        )
        
        for account in connected_accounts.items:
            if account.status == "ACTIVE":
                config.connection_id = account.id
                return True
            else:
                print(f"[warning] Inactive account {account.id} found for user: {config.user_id}")
        
        return False
    except Exception as e:
        print(f"Error checking connected accounts: {e}")
        return False


def get_or_create_auth_config():
    """Get existing Gmail auth config or create a new one."""
    if not composio_client:
        raise ValueError("Composio client not initialized")
    
    # Check for existing auth config
    if config.gmail_auth_config_id:
        try:
            auth_configs = composio_client.auth_configs.list()
            for auth_config in auth_configs.items:
                if auth_config.id == config.gmail_auth_config_id:
                    return auth_config
        except Exception:
            pass
    
    # Look for existing Gmail auth config
    try:
        auth_configs = composio_client.auth_configs.list()
        for auth_config in auth_configs.items:
            if auth_config.toolkit == "GMAIL":
                config.gmail_auth_config_id = auth_config.id
                return auth_config
    except Exception:
        pass
    
    # Create new auth config
    auth_config = composio_client.auth_configs.create(
        toolkit="GMAIL",
        options={
            "name": "email_agent_gmail_auth",
            "type": "use_custom_auth",
            "auth_scheme": "OAUTH2",
            "credentials": {
                "client_id": config.gmail_client_id,
                "client_secret": config.gmail_client_secret,
            },
        },
    )
    config.gmail_auth_config_id = auth_config.id
    return auth_config


def authenticate_gmail():
    """Initiate Gmail OAuth2 authentication flow."""
    if not composio_client:
        raise ValueError("Composio client not initialized")
    
    auth_config = get_or_create_auth_config()
    
    connection_request = composio_client.connected_accounts.initiate(
        user_id=config.user_id,
        auth_config_id=auth_config.id,
    )
    
    print(f"\n{'='*60}")
    print("Gmail Authentication Required")
    print(f"{'='*60}")
    print(f"\nPlease visit this URL to authenticate:")
    print(f"\n{connection_request.redirect_url}\n")
    print(f"{'='*60}\n")
    
    # Try to open browser automatically
    try:
        webbrowser.open(connection_request.redirect_url)
    except Exception:
        pass
    
    # Wait for authentication
    print("Waiting for authentication... (timeout: 120 seconds)")
    connection_request.wait_for_connection(timeout=120)
    
    config.connection_id = connection_request.id
    print("\n✓ Gmail authentication successful!")
    return connection_request.id


def run_gmail_agent(prompt: str) -> dict:
    """Run the Gmail agent with a prompt."""
    if not all([composio_client, openai_client]):
        raise ValueError("Clients not initialized")
    
    if not check_connected_account_exists():
        raise ValueError("Gmail not authenticated. Please authenticate first.")
    
    # Get available Gmail tools
    tools = composio_client.tools.get(
        user_id=config.user_id,
        tools=[
            "GMAIL_FETCH_EMAILS",
            "GMAIL_SEND_EMAIL",
            "GMAIL_CREATE_EMAIL_DRAFT",
            "GMAIL_LIST_DRAFTS",
            "GMAIL_SEND_DRAFT",
            "GMAIL_DELETE_DRAFT",
            "GMAIL_REPLY_TO_THREAD",
            "GMAIL_GET_THREAD",
            "GMAIL_LIST_THREADS",
            "GMAIL_ADD_LABEL_TO_EMAIL",
            "GMAIL_REMOVE_LABEL_FROM_EMAIL",
            "GMAIL_LIST_LABELS",
            "GMAIL_CREATE_LABEL",
        ]
    )
    
    # Generate response using OpenAI
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        tools=tools,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful Gmail assistant. You help users manage their emails, send messages, create drafts, and organize their inbox. Be concise and helpful."
            },
            {"role": "user", "content": prompt}
        ],
    )
    
    # Handle tool calls if any
    result = composio_client.provider.handle_tool_calls(
        user_id=config.user_id,
        response=response
    )
    
    return {
        "response": response.choices[0].message.content if response.choices[0].message.content else "Action completed",
        "tool_results": result if result else []
    }


# ============================================================================
# Flask Routes
# ============================================================================

@app.route('/')
def home():
    """Home endpoint with API documentation."""
    return jsonify({
        "name": "Email Agent API",
        "version": "1.0.0",
        "description": "Gmail actions powered by Composio",
        "endpoints": {
            "GET /": "API documentation",
            "GET /status": "Check authentication status",
            "GET /config": "View current configuration (masked)",
            "POST /config": "Update configuration",
            "POST /authenticate": "Initiate Gmail authentication",
            "POST /logout": "Clear authentication",
            "POST /query": "Execute Gmail action with natural language",
            "POST /send": "Send an email",
            "POST /draft": "Create an email draft",
            "GET /emails": "Fetch recent emails",
            "GET /drafts": "List email drafts",
            "GET /labels": "List Gmail labels",
        }
    })


@app.route('/status')
def status():
    """Check authentication and configuration status."""
    return jsonify({
        "configured": config.is_configured(),
        "authenticated": check_connected_account_exists(),
        "user_id": config.user_id,
        "missing_credentials": config.get_missing_credentials() if not config.is_configured() else [],
    })


@app.route('/config', methods=['GET'])
def get_config():
    """Get current configuration (sensitive data masked)."""
    return jsonify(config.to_dict())


@app.route('/config', methods=['POST'])
def update_config():
    """Update configuration credentials."""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    config.set_credentials(
        composio_api_key=data.get('composio_api_key'),
        openai_api_key=data.get('openai_api_key'),
        gmail_client_id=data.get('gmail_client_id'),
        gmail_client_secret=data.get('gmail_client_secret'),
        user_id=data.get('user_id'),
    )
    
    # Reinitialize clients with new credentials
    try:
        initialize_clients()
        return jsonify({
            "success": True,
            "message": "Configuration updated",
            "configured": config.is_configured()
        })
    except Exception as e:
        return jsonify({
            "success": True,
            "message": f"Configuration saved but clients not initialized: {str(e)}",
            "configured": config.is_configured()
        })


@app.route('/authenticate', methods=['POST'])
def authenticate():
    """Initiate Gmail OAuth2 authentication."""
    if not config.is_configured():
        return jsonify({
            "error": "Missing credentials",
            "missing": config.get_missing_credentials()
        }), 400
    
    try:
        initialize_clients()
        
        # Check if already authenticated
        if check_connected_account_exists():
            return jsonify({
                "success": True,
                "message": "Already authenticated",
                "connection_id": config.connection_id
            })
        
        # Start authentication flow (this will block)
        connection_id = authenticate_gmail()
        
        return jsonify({
            "success": True,
            "message": "Authentication successful",
            "connection_id": connection_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/logout', methods=['POST'])
def logout():
    """Clear authentication data."""
    config.clear_auth()
    return jsonify({
        "success": True,
        "message": "Authentication cleared"
    })


@app.route('/query', methods=['POST'])
def query():
    """Execute a Gmail action using natural language."""
    data = request.get_json()
    
    if not data or 'query' not in data:
        return jsonify({"error": "Missing 'query' in request body"}), 400
    
    try:
        result = run_gmail_agent(data['query'])
        return jsonify({
            "success": True,
            **result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/send', methods=['POST'])
def send_email():
    """Send an email."""
    data = request.get_json()
    
    required = ['to', 'subject', 'body']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    
    prompt = f"""Send an email to {data['to']} with:
    Subject: {data['subject']}
    Body: {data['body']}
    {"CC: " + data['cc'] if data.get('cc') else ""}
    {"BCC: " + data['bcc'] if data.get('bcc') else ""}"""
    
    try:
        result = run_gmail_agent(prompt)
        return jsonify({
            "success": True,
            **result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/draft', methods=['POST'])
def create_draft():
    """Create an email draft."""
    data = request.get_json()
    
    required = ['to', 'subject', 'body']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
    
    prompt = f"""Create an email draft to {data['to']} with:
    Subject: {data['subject']}
    Body: {data['body']}
    {"CC: " + data['cc'] if data.get('cc') else ""}"""
    
    try:
        result = run_gmail_agent(prompt)
        return jsonify({
            "success": True,
            **result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/emails', methods=['GET'])
def get_emails():
    """Fetch recent emails."""
    max_results = request.args.get('max', 10, type=int)
    label = request.args.get('label', 'INBOX')
    
    prompt = f"Fetch the {max_results} most recent emails from the {label} folder. Show me the sender, subject, and a brief preview of each email."
    
    try:
        result = run_gmail_agent(prompt)
        return jsonify({
            "success": True,
            **result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/drafts', methods=['GET'])
def list_drafts():
    """List email drafts."""
    max_results = request.args.get('max', 10, type=int)
    
    prompt = f"List my {max_results} most recent email drafts with their subjects and recipients."
    
    try:
        result = run_gmail_agent(prompt)
        return jsonify({
            "success": True,
            **result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/labels', methods=['GET'])
def list_labels():
    """List Gmail labels."""
    prompt = "List all my Gmail labels."
    
    try:
        result = run_gmail_agent(prompt)
        return jsonify({
            "success": True,
            **result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Main Entry Point
# ============================================================================

def startup_check():
    """Perform startup checks for authentication and configuration."""
    print("\n" + "="*60)
    print("Email Agent - Startup Check")
    print("="*60 + "\n")
    
    # Check configuration
    if not config.is_configured():
        missing = config.get_missing_credentials()
        print("⚠ Missing credentials:")
        for cred in missing:
            print(f"  - {cred}")
        print("\nPlease set credentials via POST /config or environment variables:")
        print("  - COMPOSIO_API_KEY")
        print("  - OPENAI_API_KEY")
        print("  - GMAIL_CLIENT_ID")
        print("  - GMAIL_CLIENT_SECRET")
        print("\nServer will start but Gmail actions won't work until configured.\n")
        return False
    
    print("✓ All credentials configured")
    
    # Initialize clients
    try:
        initialize_clients()
        print("✓ Clients initialized")
    except Exception as e:
        print(f"✗ Failed to initialize clients: {e}")
        return False
    
    # Check Gmail authentication
    if check_connected_account_exists():
        print("✓ Gmail authenticated")
        print(f"  User ID: {config.user_id}")
        print(f"  Connection ID: {config.connection_id}")
        return True
    else:
        print("⚠ Gmail not authenticated")
        print("\nWould you like to authenticate Gmail now? (y/n): ", end="")
        
        try:
            response = input().strip().lower()
            if response == 'y':
                authenticate_gmail()
                return True
        except (EOFError, KeyboardInterrupt):
            print("\n")
        
        print("You can authenticate later via POST /authenticate\n")
        return False


def main():
    """Main entry point."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                    Email Agent v1.0                       ║
║          Gmail Actions powered by Composio                ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Perform startup checks
    is_ready = startup_check()
    
    if is_ready:
        print("\n✓ Email Agent is ready!")
    else:
        print("\n⚠ Email Agent starting in limited mode")
    
    print(f"\n🚀 Starting server at http://{config.flask_host}:{config.flask_port}")
    print("   Press Ctrl+C to stop\n")
    
    # Start Flask server
    app.run(
        host=config.flask_host,
        port=config.flask_port,
        debug=config.flask_debug
    )


if __name__ == "__main__":
    main()
