#!/usr/bin/env python3
"""
Setup script for Yad2 Telegram Bot
This script helps initialize the database and test the configuration
"""

import os
import sys
from dotenv import load_dotenv
from database import VehicleDatabase
from config import validate_environment
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_setup():
    """Test database connection and create tables"""
    print("🗄️  Testing database setup...")
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Validate environment
        validate_environment()
        
        # Initialize database (this will create tables)
        db = VehicleDatabase()
        
        # Test basic operations
        stats = db.get_vehicle_stats()
        print(f"✅ Database setup successful!")
        print(f"   Total vehicles: {stats['total_vehicles']}")
        print(f"   Database URL: {os.getenv('DATABASE_URL', 'Not set')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {str(e)}")
        return False

def test_telegram_config():
    """Test Telegram configuration"""
    print("📱 Testing Telegram configuration...")
    
    try:
        from telegram import Bot
        
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            print("❌ TELEGRAM_BOT_TOKEN not set")
            return False
        
        # Test bot token by getting bot info
        bot = Bot(token=bot_token)
        # Note: This is a sync call, but it's just for testing
        import asyncio
        
        async def test_bot():
            bot_info = await bot.get_me()
            return bot_info
        
        bot_info = asyncio.run(test_bot())
        print(f"✅ Telegram bot configuration successful!")
        print(f"   Bot name: {bot_info.first_name}")
        print(f"   Bot username: @{bot_info.username}")
        
        # Check chat ID
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if chat_id:
            print(f"   Chat ID: {chat_id}")
        else:
            print("⚠️  TELEGRAM_CHAT_ID not set")
        
        return True
        
    except Exception as e:
        print(f"❌ Telegram configuration failed: {str(e)}")
        return False

def show_quick_start_guide():
    """Show quick start guide"""
    print("\n🚀 Quick Start Guide:")
    print("=" * 50)
    print("1. Copy env_example.txt to .env")
    print("2. Fill in your Telegram bot token and chat ID")
    print("3. Set up your PostgreSQL database")
    print("4. Update DATABASE_URL in .env")
    print("5. Run: python setup.py to test configuration")
    print("6. Run: python telegram_bot.py to start the bot")
    print("\n📖 For detailed instructions, see README.md")

def main():
    """Main setup function"""
    print("🔧 Yad2 Telegram Bot Setup")
    print("=" * 50)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("⚠️  .env file not found!")
        show_quick_start_guide()
        return
    
    # Load environment
    load_dotenv()
    
    # Run tests
    tests = [
        ("Database", test_database_setup),
        ("Telegram", test_telegram_config),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n🧪 {name} Test:")
        if test_func():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Setup Summary: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Setup complete! You can now run the bot:")
        print("   python telegram_bot.py")
    else:
        print("❌ Setup incomplete. Please fix the issues above.")
        show_quick_start_guide()

if __name__ == "__main__":
    main() 