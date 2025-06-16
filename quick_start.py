#!/usr/bin/env python3
"""
Quick Start Guide for Yad2 Telegram Bot
This script provides an interactive setup experience
"""

import os
import sys
from dotenv import load_dotenv

def welcome():
    """Show welcome message"""
    print("🚀 Welcome to Yad2 Telegram Bot Quick Start!")
    print("=" * 50)
    print("This script will help you set up the bot in a few simple steps.")
    print()

def check_prerequisites():
    """Check if all prerequisites are installed"""
    print("🔍 Checking prerequisites...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        return False
    else:
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} is installed")
    
    # Check if dependencies are installed
    try:
        import psycopg2
        import telegram
        print("✅ Required packages are installed")
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("Run: pip install -r requirements.txt")
        return False
    
    # Check PostgreSQL
    print("ℹ️  Make sure PostgreSQL is running on your system")
    
    return True

def guide_telegram_setup():
    """Guide user through Telegram setup"""
    print("\n📱 Telegram Bot Setup")
    print("=" * 30)
    print("1. Create a new bot:")
    print("   - Message @BotFather on Telegram")
    print("   - Send /newbot")
    print("   - Follow the prompts")
    print("   - Copy your bot token")
    print()
    print("2. Get your Chat ID:")
    print("   - Add your bot to the desired chat/group")
    print("   - Send a test message")
    print("   - Visit: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates")
    print("   - Find the chat ID in the response")
    print()
    input("Press Enter when you have your bot token and chat ID...")

def run_bootstrap():
    """Run the bootstrap script"""
    print("\n🔧 Running automated setup...")
    
    choice = input("Run automated database setup? (y/n) [y]: ").strip().lower()
    
    if choice in ('', 'y', 'yes'):
        print("Running bootstrap script...")
        import subprocess
        result = subprocess.run([sys.executable, 'bootstrap.py'], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Bootstrap completed successfully!")
            return True
        else:
            print("❌ Bootstrap failed:")
            print(result.stderr)
            return False
    else:
        print("⚠️  Manual setup required. Please:")
        print("  1. Set up your .env file")
        print("  2. Create PostgreSQL database")
        print("  3. Run: python migrations.py")
        return False

def test_configuration():
    """Test the bot configuration"""
    print("\n🧪 Testing configuration...")
    
    import subprocess
    result = subprocess.run([sys.executable, 'setup.py'], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Configuration test passed!")
        return True
    else:
        print("❌ Configuration test failed:")
        print(result.stderr)
        return False

def final_instructions():
    """Show final instructions"""
    print("\n🎉 Setup Complete!")
    print("=" * 30)
    print("Your Yad2 Telegram Bot is ready to use!")
    print()
    print("Next steps:")
    print("1. Customize your vehicle search configurations in telegram_bot.py")
    print("2. Start the bot: python telegram_bot.py")
    print("3. Send /start to your bot to test it")
    print()
    print("📖 For more information, check the README.md file")
    print("🐛 If you encounter issues, check the troubleshooting section")

def main():
    """Main quick start function"""
    welcome()
    
    if not check_prerequisites():
        print("\n❌ Prerequisites check failed. Please install missing requirements.")
        return
    
    guide_telegram_setup()
    
    if not run_bootstrap():
        print("\n⚠️  Setup incomplete. Please complete manual setup steps.")
        return
    
    if not test_configuration():
        print("\n⚠️  Configuration test failed. Please check your settings.")
        return
    
    final_instructions()

if __name__ == "__main__":
    main() 