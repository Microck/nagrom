#!/usr/bin/env python3
"""
Test script to verify the Discord bot setup
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config_manager import BotConfig
from src.llm.google_ai_studio import GoogleAIStudioProvider
from src.llm.openai_compatible import OpenRouterProvider

def test_config_loading():
    """Test that config loads correctly"""
    print("Testing config loading...")
    try:
        config = BotConfig.load()
        print(f"✅ Config loaded successfully")
        print(f"   Discord prefix: {config.discord.prefix}")
        print(f"   LLM provider: {config.llm.provider}")
        print(f"   LLM model: {config.llm.model}")
        return True
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False

def test_provider_creation():
    """Test LLM provider creation"""
    print("\nTesting LLM provider creation...")
    try:
        config = BotConfig.load()
        
        if config.llm.provider.lower() == "google_ai_studio":
            provider = GoogleAIStudioProvider(config.llm, "config/system_prompt.txt")
            print("✅ Google AI Studio provider created successfully")
        else:
            provider = OpenRouterProvider(config.llm, "config/system_prompt.txt")
            print(f"✅ OpenAI-compatible provider created successfully")
        
        return True
    except Exception as e:
        print(f"❌ Provider creation failed: {e}")
        return False

def test_logo_exists():
    """Test that logo file exists"""
    print("\nTesting logo file...")
    logo_path = "assets/logo/logo.png"
    if os.path.exists(logo_path):
        print(f"✅ Logo file found at {logo_path}")
        return True
    else:
        print(f"❌ Logo file not found at {logo_path}")
        return False

def main():
    print("🔍 Testing Discord Bot Setup\n")
    
    tests = [
        test_config_loading,
        test_provider_creation,
        test_logo_exists,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print(f"\n📊 Test Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("🎉 All tests passed! The bot setup should work correctly.")
        print("\n📝 To run the bot:")
        print("   1. Make sure privileged intents are enabled in Discord Developer Portal")
        print("   2. Run: . .venv/bin/activate && python -m src")
        return 0
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())