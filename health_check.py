#!/usr/bin/env python3
"""
Health check script for Yad2 Telegram Bot
This script can be used for monitoring and alerting
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Import our modules
from database import VehicleDatabase
from config import validate_environment

# Load environment
load_dotenv()

def check_database_connection():
    """Check if database is accessible"""
    try:
        db = VehicleDatabase()
        stats = db.get_vehicle_stats()
        print(f"✅ Database connection: OK")
        print(f"   Total vehicles: {stats['total_vehicles']}")
        print(f"   Unsent vehicles: {stats['unsent_vehicles']}")
        return True
    except Exception as e:
        print(f"❌ Database connection: FAILED - {str(e)}")
        return False

def check_environment():
    """Check if all required environment variables are set"""
    try:
        validate_environment()
        print("✅ Environment variables: OK")
        return True
    except Exception as e:
        print(f"❌ Environment variables: FAILED - {str(e)}")
        return False

def check_recent_activity():
    """Check if there has been recent activity in the database"""
    try:
        db = VehicleDatabase()
        
        # Check if there are vehicles added in the last 24 hours
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) as recent_count 
                    FROM vehicles 
                    WHERE first_seen > NOW() - INTERVAL '24 hours'
                """)
                recent_count = cur.fetchone()[0]
                
                cur.execute("""
                    SELECT MAX(first_seen) as last_activity
                    FROM vehicles
                """)
                last_activity = cur.fetchone()[0]
        
        if recent_count > 0:
            print(f"✅ Recent activity: {recent_count} vehicles added in last 24h")
        else:
            print(f"⚠️  Recent activity: No vehicles added in last 24h")
            if last_activity:
                print(f"   Last activity: {last_activity}")
        
        return True
    except Exception as e:
        print(f"❌ Recent activity check: FAILED - {str(e)}")
        return False

def main():
    """Run all health checks"""
    print(f"🏥 Yad2 Telegram Bot Health Check - {datetime.now()}")
    print("=" * 50)
    
    checks = [
        ("Environment", check_environment),
        ("Database", check_database_connection),
        ("Activity", check_recent_activity),
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        print(f"\n🔍 Checking {name}...")
        if check_func():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Health Check Summary: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All systems operational!")
        sys.exit(0)
    else:
        print("⚠️  Some issues detected")
        sys.exit(1)

if __name__ == "__main__":
    main() 