from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

_CONFIG_CACHE: Optional[Dict[str, Any]] = None


def _get_config_path() -> Path:
    """Get the path to the config file, checking multiple locations."""
    # Try current directory first, then parent directories
    current_dir = Path(__file__).parent
    for path in [current_dir, current_dir.parent]:
        config_file = path / "config.json"
        if config_file.exists():
            return config_file

    # If not found, return the expected path in the api directory
    return current_dir / "config.json"


def load_config() -> Dict[str, Any]:
    """Load configuration from config.json file."""
    global _CONFIG_CACHE

    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    config_path = _get_config_path()

    if not config_path.exists():
        # Return default config if file doesn't exist
        _CONFIG_CACHE = {
            "openai": {
                "api_key": "",
                "model": "gpt-4o-mini"
            },
            "settings": {
                "llm_enabled": True,
                "rewrite_timeout": 30
            }
        }
        return _CONFIG_CACHE

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            _CONFIG_CACHE = json.load(f)
        return _CONFIG_CACHE
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Failed to load config from {config_path}: {e}")
        # Return default config on error
        _CONFIG_CACHE = {
            "openai": {
                "api_key": "",
                "model": "gpt-4o-mini"
            },
            "settings": {
                "llm_enabled": True,
                "rewrite_timeout": 30
            }
        }
        return _CONFIG_CACHE


def get_openai_api_key() -> Optional[str]:
    """Get OpenAI API key from config, fallback to environment variable."""
    config = load_config()

    # Try config file first
    api_key = config.get("openai", {}).get("api_key", "").strip()
    if api_key:
        return api_key

    # Fallback to environment variable
    env_key = os.getenv("OPENAI_API_KEY", "").strip()
    if env_key:
        return env_key

    return None


def get_openai_model() -> str:
    """Get OpenAI model from config."""
    config = load_config()
    return config.get("openai", {}).get("model", "gpt-4o-mini")


def is_llm_enabled() -> bool:
    """Check if LLM functionality is enabled."""
    config = load_config()
    return config.get("settings", {}).get("llm_enabled", True)


def reload_config():
    """Force reload of configuration from file."""
    global _CONFIG_CACHE
    _CONFIG_CACHE = None
    return load_config()
