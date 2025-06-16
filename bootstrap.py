#!/usr/bin/env python3
"""
Bootstrap script for Yad2 Telegram Bot
This script handles complete database setup including creating the database and user
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import logging
import getpass
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def parse_database_url(database_url):
    """Parse DATABASE_URL into components"""
    parsed = urlparse(database_url)
    return {
        'host': parsed.hostname or 'localhost',
        'port': parsed.port or 5432,
        'user': parsed.username,
        'password': parsed.password,
        'database': parsed.path.lstrip('/') if parsed.path else None
    }

def get_postgres_admin_connection():
    """Get admin connection to PostgreSQL (to create database and user)"""
    print("🔐 PostgreSQL Admin Setup")
    print("To create the database and user, we need admin credentials.")
    print("Usually this is the 'postgres' user or your system user.")
    
    host = input("PostgreSQL host [localhost]: ").strip() or 'localhost'
    port = input("PostgreSQL port [5432]: ").strip() or '5432'
    admin_user = input("Admin username [postgres]: ").strip() or 'postgres'
    admin_password = getpass.getpass("Admin password: ")
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=admin_user,
            password=admin_password,
            database='postgres'  # Connect to default postgres database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn, host, port
    except psycopg2.Error as e:
        logger.error(f"Failed to connect as admin: {e}")
        return None, None, None

def create_database_and_user(admin_conn, db_name, db_user, db_password):
    """Create database and user if they don't exist"""
    cursor = admin_conn.cursor()
    
    try:
        # Check if user exists
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (db_user,))
        user_exists = cursor.fetchone()
        
        if not user_exists:
            print(f"👤 Creating user '{db_user}'...")
            cursor.execute(f"CREATE USER {db_user} WITH PASSWORD %s", (db_password,))
            logger.info(f"User '{db_user}' created successfully")
        else:
            print(f"👤 User '{db_user}' already exists")
            # Update password just in case
            cursor.execute(f"ALTER USER {db_user} WITH PASSWORD %s", (db_password,))
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        db_exists = cursor.fetchone()
        
        if not db_exists:
            print(f"🗄️  Creating database '{db_name}'...")
            cursor.execute(f"CREATE DATABASE {db_name} OWNER {db_user}")
            logger.info(f"Database '{db_name}' created successfully")
        else:
            print(f"🗄️  Database '{db_name}' already exists")
        
        # Grant privileges
        print(f"🔑 Granting privileges...")
        cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user}")
        
        return True
        
    except psycopg2.Error as e:
        logger.error(f"Failed to create database/user: {e}")
        return False
    finally:
        cursor.close()

def setup_database_from_url(database_url):
    """Setup database using DATABASE_URL"""
    db_config = parse_database_url(database_url)
    
    if not all([db_config['user'], db_config['password'], db_config['database']]):
        logger.error("DATABASE_URL must include username, password, and database name")
        return False
    
    # Get admin connection
    admin_conn, host, port = get_postgres_admin_connection()
    if not admin_conn:
        return False
    
    try:
        # Create database and user
        success = create_database_and_user(
            admin_conn, 
            db_config['database'], 
            db_config['user'], 
            db_config['password']
        )
        
        if success:
            # Test the application connection
            print("🧪 Testing application database connection...")
            from database import VehicleDatabase
            
            db = VehicleDatabase(database_url)
            stats = db.get_vehicle_stats()
            
            print("✅ Database setup completed successfully!")
            print(f"   Database: {db_config['database']}")
            print(f"   User: {db_config['user']}")
            print(f"   Host: {db_config['host']}")
            print(f"   Port: {db_config['port']}")
            print(f"   Total vehicles: {stats['total_vehicles']}")
            return True
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        return False
    finally:
        admin_conn.close()
    
    return False

def interactive_database_setup():
    """Interactive database setup"""
    print("🗄️  Interactive Database Setup")
    print("=" * 40)
    
    db_name = input("Database name [yad2_vehicles]: ").strip() or 'yad2_vehicles'
    db_user = input("Database user [yad2_user]: ").strip() or 'yad2_user'
    db_password = getpass.getpass("Database password: ")
    
    if not db_password:
        logger.error("Password is required")
        return False
    
    # Get admin connection
    admin_conn, host, port = get_postgres_admin_connection()
    if not admin_conn:
        return False
    
    try:
        # Create database and user
        success = create_database_and_user(admin_conn, db_name, db_user, db_password)
        
        if success:
            # Generate DATABASE_URL
            database_url = f"postgresql://{db_user}:{db_password}@{host}:{port}/{db_name}"
            
            print(f"\n✅ Database setup completed!")
            print(f"📝 Add this to your .env file:")
            print(f"DATABASE_URL={database_url}")
            
            # Test connection
            print("\n🧪 Testing connection...")
            from database import VehicleDatabase
            db = VehicleDatabase(database_url)
            stats = db.get_vehicle_stats()
            
            print("🎉 Everything is working perfectly!")
            return True
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        return False
    finally:
        admin_conn.close()
    
    return False

def check_env_file():
    """Check and create .env file if needed"""
    if not os.path.exists('.env'):
        print("📝 .env file not found. Creating from example...")
        if os.path.exists('env_example.txt'):
            import shutil
            shutil.copy('env_example.txt', '.env')
            print("✅ .env file created from env_example.txt")
            print("📝 Please edit .env file and add your configuration")
            return False
        else:
            print("❌ env_example.txt not found")
            return False
    return True

def main():
    """Main bootstrap function"""
    print("🚀 Yad2 Telegram Bot Bootstrap")
    print("=" * 50)
    
    # Check .env file
    if not check_env_file():
        return
    
    # Load environment
    load_dotenv()
    
    database_url = os.getenv('DATABASE_URL')
    
    if database_url and database_url != 'your_database_url_here':
        print("🔍 Found DATABASE_URL in .env file")
        choice = input("Use existing DATABASE_URL? (y/n) [y]: ").strip().lower()
        
        if choice in ('', 'y', 'yes'):
            if setup_database_from_url(database_url):
                print("\n🎉 Bootstrap completed! You can now run:")
                print("   python telegram_bot.py")
            return
    
    # Interactive setup
    if interactive_database_setup():
        print("\n🎉 Bootstrap completed! Remember to update your .env file and run:")
        print("   python telegram_bot.py")

if __name__ == "__main__":
    main() 