"""
Configuration file for Yad2 Telegram Bot
"""
import os
from typing import List, Dict
from urllib.parse import urlparse, parse_qs

# Vehicle search configurations
# Example URL format:
# https://www.yad2.co.il/vehicles/cars?manufacturer=17&model=10182&price=-1-60000&km=-1-100000

VEHICLE_CONFIGS: List[Dict] = [
    {
        'url': 'https://www.yad2.co.il/vehicles/cars?manufacturer=17&model=10182&price=-1-60000&km=-1-100000',
        'name': 'Honda Civic',
        'max_pages': 5,
        'enabled': True
    },
]

def parse_yad2_url(url: str) -> Dict:
    """Parse Yad2 URL to extract search parameters"""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    # Convert single-item lists to single values
    params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
    
    return {
        'manufacturer': int(params.get('manufacturer', 0)),
        'model': int(params.get('model', 0)),
        'price_range': params.get('price', None),
        'km_range': params.get('km', None),
        # Add more parameters as needed
    }

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
    """Get only enabled vehicle configurations with parsed URL parameters"""
    enabled_configs = [config for config in VEHICLE_CONFIGS if config.get('enabled', True)]
    for config in enabled_configs:
        config.update(parse_yad2_url(config['url']))
    return enabled_configs

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