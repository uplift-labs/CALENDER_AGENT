"""
Email Agent - Flask server for Gmail actions using Composio
OAuth2 authentication with credential storage for .exe deployment
"""

import os
import sys
import webbrowser
from typing import Optional
from flask import Flask, request, jsonify
import json

from config import config

# Set environment variables from config before importing Composio
if config.composio_api_key:
    os.environ['COMPOSIO_API_KEY'] = config.composio_api_key
if config.openai_api_key:
    os.environ['OPENAI_API_KEY'] = config.openai_api_key

from composio import Composio
from openai import AzureOpenAI

app = Flask(__name__)

# Global clients
composio_client: Optional[Composio] = None
openai_client: Optional[AzureOpenAI] = None


def initialize_clients():
    """Initialize Composio and Azure OpenAI clients."""
    global composio_client, openai_client
    
    if not config.is_configured():
        missing = config.get_missing_credentials()
        raise ValueError(f"Missing credentials: {', '.join(missing)}")
    
    composio_client = Composio(api_key=config.composio_api_key)
    openai_client = AzureOpenAI(
        api_key=config.openai_api_key,
        api_version=config.openai_api_version,
        azure_endpoint=config.azure_openai_endpoint,
    )


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
    """Get existing Gmail auth config or create a new one using Composio managed auth."""
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
            if hasattr(auth_config, 'toolkit') and auth_config.toolkit == "GMAIL":
                config.gmail_auth_config_id = auth_config.id
                return auth_config
    except Exception:
        pass
    
    # Create new auth config using Composio's managed authentication
    # No need for your own Gmail OAuth credentials!
    auth_config = composio_client.auth_configs.create(
        toolkit="GMAIL",
        options={
            "name": "email_agent_gmail_auth",
            "type": "use_composio_managed_auth",  # Uses Composio's OAuth credentials
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


def truncate_result(result: str, max_chars: int = 15000) -> str:
    """Truncate tool result to avoid token limits."""
    if len(result) <= max_chars:
        return result
    return result[:max_chars] + "\n\n... [truncated due to length]"


def run_gmail_agent(prompt: str) -> str:
    """Run the Gmail agent with a prompt and return a natural language response."""
    if not all([composio_client, openai_client]):
        raise ValueError("Clients not initialized")
    
    if not check_connected_account_exists():
        raise ValueError("Gmail not authenticated. Please authenticate first.")
    
    # Get essential Gmail tools only (reduced set to avoid large function definitions)
    tools = composio_client.tools.get(
        user_id=config.user_id,
        tools=[
            "GMAIL_FETCH_EMAILS",
            "GMAIL_SEND_EMAIL",
            "GMAIL_CREATE_EMAIL_DRAFT",
            "GMAIL_LIST_LABELS",
        ]
    )
    
    # Build conversation messages
    messages = [
        {
            "role": "system",
            "content": """You are a helpful Gmail assistant. Help users manage emails concisely.
When fetching emails, request only a small number (max 5) unless user asks for more.
After actions, give a brief summary. Keep responses short and clear."""
        },
        {"role": "user", "content": prompt}
    ]
    
    # Agentic loop - keep processing until we get a final response
    max_iterations = 5
    for _ in range(max_iterations):
        # Generate response using Azure OpenAI
        response = openai_client.chat.completions.create(
            model=config.azure_openai_deployment,
            tools=tools,
            messages=messages,
        )
        
        assistant_message = response.choices[0].message
        
        # If no tool calls, return the final response
        if not assistant_message.tool_calls:
            return assistant_message.content or "Done!"
        
        # Add assistant message to conversation
        messages.append(assistant_message)
        
        # Execute each tool call and add results to conversation
        for tool_call in assistant_message.tool_calls:
            # Execute the tool using Composio
            tool_result = composio_client.provider.execute_tool_call(
                user_id=config.user_id,
                tool_call=tool_call,
            )
            
            # Truncate large results to avoid token limits
            result_str = str(tool_result) if tool_result else "Action completed successfully."
            result_str = truncate_result(result_str)
            
            # Add tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_str
            })
    
    return "I've completed the requested actions."


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
            "POST /authenticate": "Initiate Gmail authentication",
            "POST /query": "Execute Gmail action with natural language prompt",
        },
        "example": {
            "endpoint": "POST /query",
            "body": {"query": "Show me my last 5 emails"},
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


@app.route('/query', methods=['POST'])
def query():
    """Execute a Gmail action using natural language."""
    data = request.get_json()
    
    if not data or 'query' not in data:
        return jsonify({"error": "Missing 'query' in request body"}), 400
    
    try:
        response = run_gmail_agent(data['query'])
        return jsonify({
            "success": True,
            "response": response
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
        print("  - OPENAI_API_KEY (Azure OpenAI)")
        print("  - AZURE_OPENAI_ENDPOINT")
        print("  - AZURE_OPENAI_DEPLOYMENT (optional, defaults to gpt-4o)")
        print("  - OPENAI_API_VERSION (optional)")
        print("\nNote: Gmail OAuth is handled by Composio - no Google credentials needed!")
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
