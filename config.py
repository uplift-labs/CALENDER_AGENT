"""
Configuration management for Email Agent
Handles credential storage and retrieval for .exe deployment
"""

import os
import json
from pathlib import Path
from typing import Optional

# Get the directory where the script/exe is located
def get_app_dir() -> Path:
    """Get the application directory for storing config files."""
    # For .exe, use the directory where the executable is located
    # For development, use the current working directory
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe
        app_dir = Path(sys.executable).parent
    else:
        # Running as script
        app_dir = Path(__file__).parent
    
    return app_dir


import sys

# Configuration file paths
APP_DIR = get_app_dir()
CONFIG_FILE = APP_DIR / "credentials.json"
AUTH_CONFIG_FILE = APP_DIR / "auth_config.json"


class Config:
    """Configuration manager for the Email Agent."""
    
    def __init__(self):
        self._config = self._load_config()
        self._auth_config = self._load_auth_config()
    
    def _load_config(self) -> dict:
        """Load configuration from file."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self._config, f, indent=2)
    
    def _load_auth_config(self) -> dict:
        """Load authentication configuration."""
        if AUTH_CONFIG_FILE.exists():
            try:
                with open(AUTH_CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save_auth_config(self) -> None:
        """Save authentication configuration."""
        with open(AUTH_CONFIG_FILE, 'w') as f:
            json.dump(self._auth_config, f, indent=2)
    
    # Composio API Key
    @property
    def composio_api_key(self) -> Optional[str]:
        """Get Composio API key."""
        return self._config.get('composio_api_key') or os.getenv('COMPOSIO_API_KEY')
    
    @composio_api_key.setter
    def composio_api_key(self, value: str) -> None:
        """Set Composio API key."""
        self._config['composio_api_key'] = value
        self._save_config()
    
    # Azure OpenAI Configuration
    @property
    def openai_api_key(self) -> Optional[str]:
        """Get Azure OpenAI API key."""
        return self._config.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
    
    @openai_api_key.setter
    def openai_api_key(self, value: str) -> None:
        """Set Azure OpenAI API key."""
        self._config['openai_api_key'] = value
        self._save_config()
    
    @property
    def azure_openai_endpoint(self) -> Optional[str]:
        """Get Azure OpenAI endpoint."""
        return self._config.get('azure_openai_endpoint') or os.getenv('AZURE_OPENAI_ENDPOINT')
    
    @azure_openai_endpoint.setter
    def azure_openai_endpoint(self, value: str) -> None:
        """Set Azure OpenAI endpoint."""
        self._config['azure_openai_endpoint'] = value
        self._save_config()
    
    @property
    def openai_api_version(self) -> str:
        """Get Azure OpenAI API version."""
        return self._config.get('openai_api_version') or os.getenv('OPENAI_API_VERSION', '2024-12-01-preview')
    
    @openai_api_version.setter
    def openai_api_version(self, value: str) -> None:
        """Set Azure OpenAI API version."""
        self._config['openai_api_version'] = value
        self._save_config()
    
    @property
    def azure_openai_deployment(self) -> str:
        """Get Azure OpenAI deployment name."""
        return self._config.get('azure_openai_deployment') or os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o')
    
    @azure_openai_deployment.setter
    def azure_openai_deployment(self, value: str) -> None:
        """Set Azure OpenAI deployment name."""
        self._config['azure_openai_deployment'] = value
        self._save_config()
    
    # Gmail OAuth Credentials
    @property
    def gmail_client_id(self) -> Optional[str]:
        """Get Gmail OAuth client ID."""
        return self._config.get('gmail_client_id') or os.getenv('GMAIL_CLIENT_ID')
    
    @gmail_client_id.setter
    def gmail_client_id(self, value: str) -> None:
        """Set Gmail OAuth client ID."""
        self._config['gmail_client_id'] = value
        self._save_config()
    
    @property
    def gmail_client_secret(self) -> Optional[str]:
        """Get Gmail OAuth client secret."""
        return self._config.get('gmail_client_secret') or os.getenv('GMAIL_CLIENT_SECRET')
    
    @gmail_client_secret.setter
    def gmail_client_secret(self, value: str) -> None:
        """Set Gmail OAuth client secret."""
        self._config['gmail_client_secret'] = value
        self._save_config()
    
    # User and Connection IDs
    @property
    def user_id(self) -> str:
        """Get user ID."""
        return self._config.get('user_id', 'default_user')
    
    @user_id.setter
    def user_id(self, value: str) -> None:
        """Set user ID."""
        self._config['user_id'] = value
        self._save_config()
    
    @property
    def connection_id(self) -> Optional[str]:
        """Get Gmail connection ID."""
        return self._auth_config.get('connection_id')
    
    @connection_id.setter
    def connection_id(self, value: str) -> None:
        """Set Gmail connection ID."""
        self._auth_config['connection_id'] = value
        self._save_auth_config()
    
    @property
    def gmail_auth_config_id(self) -> Optional[str]:
        """Get Gmail auth config ID."""
        return self._auth_config.get('gmail_auth_config_id')
    
    @gmail_auth_config_id.setter
    def gmail_auth_config_id(self, value: str) -> None:
        """Set Gmail auth config ID."""
        self._auth_config['gmail_auth_config_id'] = value
        self._save_auth_config()
    
    # Flask Configuration
    @property
    def flask_host(self) -> str:
        """Get Flask host."""
        return self._config.get('flask_host', '0.0.0.0')
    
    @property
    def flask_port(self) -> int:
        """Get Flask port."""
        return self._config.get('flask_port', 5001)
    
    @property
    def flask_debug(self) -> bool:
        """Get Flask debug mode."""
        return self._config.get('flask_debug', False)
    
    def is_configured(self) -> bool:
        """Check if required credentials are configured."""
        return all([
            self.composio_api_key,
            self.openai_api_key,
            self.azure_openai_endpoint,
        ])
    
    def is_authenticated(self) -> bool:
        """Check if Gmail is authenticated."""
        return bool(self.connection_id)
    
    def get_missing_credentials(self) -> list:
        """Get list of missing credentials."""
        missing = []
        if not self.composio_api_key:
            missing.append('composio_api_key')
        if not self.openai_api_key:
            missing.append('openai_api_key')
        if not self.azure_openai_endpoint:
            missing.append('azure_openai_endpoint')
        return missing
    
    def set_credentials(
        self,
        composio_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        azure_openai_endpoint: Optional[str] = None,
        openai_api_version: Optional[str] = None,
        azure_openai_deployment: Optional[str] = None,
        gmail_client_id: Optional[str] = None,
        gmail_client_secret: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """Set multiple credentials at once."""
        if composio_api_key:
            self.composio_api_key = composio_api_key
        if openai_api_key:
            self.openai_api_key = openai_api_key
        if azure_openai_endpoint:
            self.azure_openai_endpoint = azure_openai_endpoint
        if openai_api_version:
            self.openai_api_version = openai_api_version
        if azure_openai_deployment:
            self.azure_openai_deployment = azure_openai_deployment
        if gmail_client_id:
            self.gmail_client_id = gmail_client_id
        if gmail_client_secret:
            self.gmail_client_secret = gmail_client_secret
        if user_id:
            self.user_id = user_id
    
    def clear_auth(self) -> None:
        """Clear authentication data."""
        self._auth_config = {}
        self._save_auth_config()
    
    def to_dict(self) -> dict:
        """Get all configuration as dictionary (sensitive data masked)."""
        return {
            'composio_api_key': '***' if self.composio_api_key else None,
            'openai_api_key': '***' if self.openai_api_key else None,
            'azure_openai_endpoint': self.azure_openai_endpoint,
            'openai_api_version': self.openai_api_version,
            'azure_openai_deployment': self.azure_openai_deployment,
            'gmail_client_id': '***' if self.gmail_client_id else None,
            'gmail_client_secret': '***' if self.gmail_client_secret else None,
            'user_id': self.user_id,
            'connection_id': self.connection_id,
            'gmail_auth_config_id': self.gmail_auth_config_id,
            'is_configured': self.is_configured(),
            'is_authenticated': self.is_authenticated(),
        }


# Global config instance
config = Config()

