#!/usr/bin/env python3
"""
Setup script for Smart Financial Coach API configuration.
"""

import json
import sys
from pathlib import Path


def setup_config():
    """Interactive setup for API configuration."""
    config_path = Path(__file__).parent / "config.json"

    print("=== Smart Financial Coach API Setup ===")
    print()

    # Load existing config or create new one
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            print(f"Found existing config at: {config_path}")
        except json.JSONDecodeError:
            print(
                f"Warning: Invalid JSON in {config_path}, creating new config")
            config = {}
    else:
        print(f"Creating new config at: {config_path}")
        config = {}

    # Ensure structure exists
    if "openai" not in config:
        config["openai"] = {}
    if "settings" not in config:
        config["settings"] = {}

    # Get OpenAI API key
    current_key = config.get("openai", {}).get("api_key", "")
    if current_key:
        print(f"Current OpenAI API key: {current_key[:10]}...")

    print("\nEnter your OpenAI API key (or press Enter to skip):")
    print("You can get one at: https://platform.openai.com/api-keys")
    new_key = input("API Key: ").strip()

    if new_key:
        config["openai"]["api_key"] = new_key
        print("✓ API key updated")
    elif not current_key:
        print("! No API key set - LLM features will be disabled")

    # Set other defaults
    config["openai"]["model"] = config.get(
        "openai", {}).get("model", "gpt-4o-mini")
    config["settings"]["llm_enabled"] = True
    config["settings"]["rewrite_timeout"] = 30

    # Save config
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"\n✓ Configuration saved to: {config_path}")

        # Test the configuration
        print("\nTesting configuration...")
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from app.config import get_openai_api_key, is_llm_enabled
            from app.services.llm_service import LLM_AVAILABLE

            print(f"- LLM enabled in config: {is_llm_enabled()}")
            print(f"- API key configured: {bool(get_openai_api_key())}")
            print(f"- LLM service available: {LLM_AVAILABLE}")

            if LLM_AVAILABLE:
                print("\n✓ LLM features are ready!")
            else:
                print("\n! LLM features are disabled (missing API key)")

        except Exception as e:
            print(f"! Error testing configuration: {e}")

    except IOError as e:
        print(f"Error saving config: {e}")
        return False

    return True


if __name__ == "__main__":
    setup_config()
