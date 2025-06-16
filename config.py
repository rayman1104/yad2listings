"""
Configuration file for Yad2 Telegram Bot
"""
import os
from typing import List, Dict

# Vehicle search configurations
# Find manufacturer and model IDs from Yad2 URLs like:
# https://www.yad2.co.il/vehicles/cars?manufacturer=19&model=12894

VEHICLE_CONFIGS: List[Dict] = [
    {
        'manufacturer': 17,    # Honda
        'model': 10182,        # Civic
        'name': 'Honda Civic',
        'max_pages': 5,
        'enabled': True
    },
]

# Bot settings
BOT_SETTINGS = {
    'check_interval_seconds': int(os.getenv('CHECK_INTERVAL_SECONDS', '60')),
    'max_notifications_per_check': 10,  # Limit notifications to avoid spam
    'rate_limit_delay': 2,  # Seconds between requests
    'cleanup_interval_hours': 1,  # How often to cleanup old records
    'keep_records_days': 7,  # How long to keep vehicle records
    'enable_startup_message': True,
    'enable_periodic_stats': False,  # Send periodic statistics
    'stats_interval_hours': 24,  # How often to send stats (if enabled)
}

# Message formatting settings
MESSAGE_SETTINGS = {
    'max_description_length': 200,
    'include_hashtags': True,
    'include_km_per_year': True,
    'include_production_date': True,
    'disable_web_preview': False,
    'use_markdown': True,
}

# Database settings
DATABASE_SETTINGS = {
    'connection_timeout': 30,
    'command_timeout': 60,
    'pool_size': 5,
    'max_overflow': 10,
}

def get_enabled_vehicle_configs() -> List[Dict]:
    """Get only enabled vehicle configurations"""
    return [config for config in VEHICLE_CONFIGS if config.get('enabled', True)]

def get_vehicle_config_by_name(name: str) -> Dict:
    """Get vehicle configuration by name"""
    for config in VEHICLE_CONFIGS:
        if config['name'].lower() == name.lower():
            return config
    return None

# Environment validation
def validate_environment():
    """Validate that all required environment variables are set"""
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID', 
        'DATABASE_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return True 