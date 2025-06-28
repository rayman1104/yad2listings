import asyncio
import logging
import os
import time
from datetime import datetime
from typing import List, Dict
import json
from pathlib import Path
import requests
from fake_useragent import UserAgent
from urllib.parse import urlparse, parse_qs
import random

from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from dotenv import load_dotenv

# Import our custom modules
import yad2_parser
from database import VehicleDatabase
from config import get_enabled_vehicle_configs, BOT_SETTINGS, MESSAGE_SETTINGS, validate_environment
from http_utils import http_client, fetch_vehicle_details

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class Yad2TelegramBot:
    def __init__(self):
        """Initialize the Telegram bot"""
        # Validate environment first
        validate_environment()
        
        # Get configuration from environment variables
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.check_interval = BOT_SETTINGS['check_interval_seconds']
        
        # Initialize database
        self.db = VehicleDatabase()
        
        # Create logs directory if it doesn't exist
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        
        # Initialize Telegram bot application
        self.application = Application.builder().token(self.bot_token).build()
        
        # Get enabled vehicle search configurations from config
        self.search_configs = get_enabled_vehicle_configs()
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("test", self.test_command))
        
        self.is_monitoring = False
        
        # Spam prevention for invalid response notifications
        self.invalid_response_notification_sent = False
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🚗 Yad2 Vehicle Monitor Bot

Available commands:
/start - Show this message
/status - Show monitoring status
/stats - Show database statistics
/test - Send a test message

The bot will automatically check for new vehicle ads every minute and send notifications.
        """
        await update.message.reply_text(welcome_message)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        status = "🟢 Monitoring is running" if self.is_monitoring else "🔴 Monitoring is stopped"
        
        configs_text = []
        for config in self.search_configs:
            # Extract manufacturer and model from URL
            parsed_url = urlparse(config['url'])
            params = parse_qs(parsed_url.query)
            manufacturer = params.get('manufacturer', ['Unknown'])[0]
            model = params.get('model', ['Unknown'])[0]
            
            configs_text.append(f"• {config['name']} (ID: {manufacturer}-{model})")
        
        configs_text = "\n".join(configs_text)
        
        message = f"""
{status}

Check interval: {self.check_interval} seconds

Monitored vehicles:
{configs_text}
        """
        await update.message.reply_text(message)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        try:
            stats = self.db.get_vehicle_stats()
            message = f"""
📊 Database Statistics

Total vehicles: {stats['total_vehicles']}
Unsent vehicles: {stats['unsent_vehicles']}
Unique manufacturers: {stats['unique_manufacturers']}
Unique models: {stats['unique_models']}

Oldest entry: {stats['oldest_entry']}
Newest entry: {stats['newest_entry']}
            """
            await update.message.reply_text(message)
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting stats: {str(e)}")
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /test command"""
        await update.message.reply_text("🧪 Test message from Yad2 Monitor Bot!")
    
    def format_vehicle_message(self, vehicle: Dict) -> str:
        """Format vehicle data into a nice Telegram message"""
        # Format price with thousands separator
        price_formatted = f"₪{vehicle['price']:,}" if vehicle['price'] else "Price not specified"
        
        # Format production date
        production_date = vehicle.get('productionDate', 'Unknown')
        if isinstance(production_date, str) and len(production_date) >= 7:
            production_date = production_date[:7]  # YYYY-MM format
        
        # Format km with thousands separator
        km_formatted = f"{vehicle['km']:,} km" if vehicle['km'] else "Unknown km"
        
        # Format km per year
        km_per_year = f"{vehicle.get('km_per_year', 0):,.0f} km/year"
        
        # Truncate description if too long
        description = vehicle.get('description', '')
        max_desc_length = MESSAGE_SETTINGS['max_description_length']
        if len(description) > max_desc_length:
            description = description[:max_desc_length] + "..."
        
        message = f"""
🚗 *{vehicle.get('make', 'Unknown')} {vehicle.get('model', 'Unknown')}*
{vehicle.get('subModel', '')}

💰 *Price:* {price_formatted}
📍 *Location:* {vehicle.get('city', 'Unknown')}
📅 *Production:* {production_date}
🏃 *Hand:* {vehicle.get('hand', 'Unknown')}
🛣️ *Mileage:* {km_formatted} ({km_per_year})

📝 *Description:*
{description}

🔗 [View Ad]({vehicle.get('link', '')})

#NewAd #{vehicle.get('make', '').replace(' ', '')}{vehicle.get('model', '').replace(' ', '')}
        """
        
        return message
    
    async def send_vehicle_notification(self, vehicle: Dict):
        """Send a vehicle notification to the configured chat"""
        try:
            message = self.format_vehicle_message(vehicle)
            bot = Bot(token=self.bot_token)
            await bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False
            )
            logger.info(f"Sent notification for vehicle {vehicle['token']}")
        except Exception as e:
            logger.error(f"Error sending notification for vehicle {vehicle['token']}: {str(e)}")
    
    async def send_invalid_response_notification(self, invalid_configs: List[str]):
        """Send notification about invalid responses with spam prevention"""
        if self.invalid_response_notification_sent:
            logger.info("Skipping invalid response notification due to previous notification")
            return
        
        try:
            configs_text = "\n".join([f"• {config}" for config in invalid_configs])
            
            message = f"""
⚠️ *Invalid Response Detected*

The bot received invalid responses from Yad2 for the following configurations:
{configs_text}

This usually means a captcha needs to be solved. Please:
1. Visit https://www.yad2.co.il/vehicles
2. Solve any captcha that appears
3. The bot will resume normal operation once the captcha is solved
            """
            
            bot = Bot(token=self.bot_token)
            await bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Update flag
            self.invalid_response_notification_sent = True
            logger.info(f"Sent invalid response notification for {len(invalid_configs)} configs")
            
        except Exception as e:
            logger.error(f"Error sending invalid response notification: {str(e)}")

    def save_invalid_response(self, config: Dict, response, url: str):
        """Save invalid response data for debugging"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"invalid_response_{timestamp}.log"
            filepath = self.logs_dir / filename
            
            # Prepare metadata
            metadata = {
                "timestamp": timestamp,
                "config_name": config['name'],
                "url": url,
                "response_length": len(response.content),
                "status_code": response.status_code,
                "headers": dict(response.headers)
            }
            
            with open(filepath, "w", encoding="utf-8") as f:
                # Write metadata
                f.write("=== METADATA ===\n")
                f.write(json.dumps(metadata, indent=2))
                f.write("\n\n=== RESPONSE CONTENT ===\n")
                # Write response content
                f.write(response.content.decode("utf-8", errors="replace"))
            
            logger.warning(f"Saved invalid response to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving invalid response: {str(e)}")

    def safe_format_date(self, date_str: str) -> str:
        """Safely format date string, returning empty string if invalid"""
        try:
            if not date_str or date_str.strip() == '':
                return ''
            return yad2_parser.format_date(date_str)
        except Exception as e:
            logger.warning(f"Error formatting date '{date_str}': {str(e)}")
            return ''

    async def check_for_new_vehicles(self):
        """Check for new vehicles and send notifications"""
        logger.info("Checking for new vehicles...")
        
        # Track invalid responses to send one notification for all
        invalid_configs = []
        
        for config in self.search_configs:
            try:
                url = config['url']
                max_pages = config.get('max_pages', 5)
                
                logger.info(f"Checking {config['name']} (URL: {url})")
                
                # Add delay to avoid hitting rate limits
                time.sleep(BOT_SETTINGS['rate_limit_delay'])
                
                response = http_client.get(url, include_priority=True)
                
                if not http_client.validate_response(response):
                    logger.warning(f"Response seems invalid for {config['name']}")
                    self.save_invalid_response(config, response, url)
                    invalid_configs.append(config['name'])
                    continue
                
                # Parse the data
                data = yad2_parser.extract_json_from_html(response.content.decode("utf-8"))
                listings_data = data['props']['pageProps']['dehydratedState']['queries'][0]['state']['data']
                
                # Extract manufacturer and model from URL for database storage
                parsed_url = urlparse(url)
                params = parse_qs(parsed_url.query)
                manufacturer = int(params.get('manufacturer', [0])[0])
                model = int(params.get('model', [0])[0])
                
                # Process all listing types
                all_vehicles = []
                for listing_type in ['commercial', 'private', 'solo', 'platinum']:
                    vehicles_list = listings_data.get(listing_type, [])
                    if vehicles_list:
                        # Convert to the format expected by our database
                        processed_vehicles = []
                        
                        for vehicle_raw in vehicles_list:
                            try:
                                # Check for essential fields first - use token as primary key
                                if 'token' not in vehicle_raw:
                                    logger.warning("Skipping vehicle without token")
                                    continue
                                
                                if 'vehicleDates' not in vehicle_raw:
                                    logger.warning(f"Skipping vehicle {vehicle_raw.get('token', 'unknown')} without vehicleDates")
                                    continue
                                
                                # Check if vehicle already exists in database
                                if self.db.vehicle_exists(vehicle_raw['token']):
                                    logger.debug(f"Vehicle {vehicle_raw['token']} already exists in database, skipping")
                                    continue
                                
                                # Use the same processing logic as yad2_parser but adapted for new structure
                                year = vehicle_raw['vehicleDates']['yearOfProduction']
                                month = yad2_parser.get_month_number(
                                    vehicle_raw['vehicleDates'].get('monthOfProduction', {"text": "ינואר"})['text']
                                ) if 'monthOfProduction' in vehicle_raw['vehicleDates'] else 1
                                production_date = f"{year}-{month:02d}-01"
                                
                                years_since_production = yad2_parser.calculate_years_since_production(year, month)
                                
                                # Handle missing km field - try to extract from subModel or use 0
                                km = 0
                                submodel_text = vehicle_raw.get('subModel', {}).get('text', '')
                                # Try to extract km from subModel text if available
                                import re
                                km_match = re.search(r'(\d{1,3}(?:,\d{3})*|\d+)\s*ק״מ', submodel_text)
                                if km_match:
                                    km_str = km_match.group(1).replace(',', '')
                                    km = int(km_str)
                                
                                # Extract HP from subModel text
                                hp_match = re.search(r'(\d+)\s*כ״ס', submodel_text)
                                hp = int(hp_match.group(1)) if hp_match else 0
                                
                                # Initialize description and city with default values
                                description = vehicle_raw.get("metaData", {}).get("description", '')
                                city = vehicle_raw.get('address', {}).get('area', {}).get('text', 'Unknown')
                                
                                # Only fetch details if we're missing important data AND this is a new vehicle
                                if km == 0:
                                    logger.info(f"Fetching full details for new vehicle {vehicle_raw['token']} from individual page...")
                                    vehicle_details = await fetch_vehicle_details(vehicle_raw['token'])
                                    
                                    if vehicle_details:
                                        # Update km if it was missing or if we got better data
                                        if km == 0 and 'km' in vehicle_details:
                                            km = vehicle_details['km']
                                            logger.info(f"Found KM {km} for vehicle {vehicle_raw['token']} from individual page")
                                        
                                        # Update description and location if available
                                        if 'description' in vehicle_details:
                                            description = vehicle_details['description']
                                            logger.info(f"Updated description for vehicle {vehicle_raw['token']}")
                                        if 'city' in vehicle_details:
                                            city = vehicle_details['city']
                                            logger.info(f"Updated city to '{city}' for vehicle {vehicle_raw['token']}")
                                    
                                    # Small delay to avoid overwhelming the server
                                    await asyncio.sleep(0.5)
                                
                                km_per_year = round(km / years_since_production if years_since_production > 0 else km, 2)
                                
                                # Handle missing dates - use current time or empty strings
                                current_time = datetime.now().isoformat()
                                
                                processed_vehicle = {
                                    'token': vehicle_raw['token'],  # Use token as primary key
                                    'adNumber': vehicle_raw.get('orderId', ''),  # Keep for backward compatibility
                                    'price': vehicle_raw.get('price', 0),
                                    'city': city,
                                    'adType': vehicle_raw.get('adType', ''),
                                    'model': vehicle_raw.get('model', {}).get('text', ''),
                                    'subModel': submodel_text,
                                    'hp': hp,
                                    'make': vehicle_raw.get('manufacturer', {}).get('text', ''),
                                    'productionDate': production_date,
                                    'km': km,
                                    'hand': vehicle_raw.get('hand', {}).get('id', 0),
                                    'createdAt': current_time,  # Use current time since dates are missing
                                    'updatedAt': current_time,
                                    'rebouncedAt': '',
                                    'listingType': listing_type,
                                    'number_of_years': years_since_production,
                                    'km_per_year': km_per_year,
                                    'description': description,
                                    'link': f'https://www.yad2.co.il/vehicles/item/{vehicle_raw.get("token", "")}',
                                }
                                processed_vehicles.append(processed_vehicle)
                                
                            except Exception as e:
                                logger.error(f"Error processing vehicle: {str(e)}")
                                logger.debug(f"Vehicle data: {vehicle_raw}")
                                continue
                        
                        all_vehicles.extend(processed_vehicles)
                
                if all_vehicles:
                    # Save to database and get new vehicles
                    new_vehicles = self.db.save_vehicles(all_vehicles, manufacturer, model)
                    
                    # Send notifications for new vehicles (limit to avoid spam)
                    max_notifications = BOT_SETTINGS['max_notifications_per_check']
                    vehicles_to_notify = new_vehicles[:max_notifications]
                    
                    for vehicle in vehicles_to_notify:
                        await self.send_vehicle_notification(vehicle)
                        # Mark as sent immediately
                        self.db.mark_as_sent([vehicle['token']])
                        
                        # Small delay between notifications
                        await asyncio.sleep(1)
                    
                    # If we had more vehicles than we could send, log it
                    if len(new_vehicles) > max_notifications:
                        logger.warning(f"Found {len(new_vehicles)} new vehicles for {config['name']}, but only sent {max_notifications} notifications to avoid spam")
                    
                    if new_vehicles:
                        logger.info(f"Found and sent {len(new_vehicles)} new vehicles for {config['name']}")
                    else:
                        logger.info(f"No new vehicles found for {config['name']}")
                else:
                    logger.info(f"No vehicles found for {config['name']}")
                    
            except Exception as e:
                logger.error(f"Error checking {config['name']}: {str(e)}")
                continue

        # Send one notification for all invalid responses
        if invalid_configs:
            await self.send_invalid_response_notification(invalid_configs)
        else:
            # Reset the flag if all responses were valid
            if self.invalid_response_notification_sent:
                logger.info("All responses are now valid, resetting invalid response notification flag")
                self.invalid_response_notification_sent = False

    async def monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Starting monitoring loop...")
        self.is_monitoring = True
        
        while self.is_monitoring:
            try:
                await self.check_for_new_vehicles()
                
                # Clean up old vehicles periodically
                current_time = time.time()
                cleanup_interval = BOT_SETTINGS['cleanup_interval_hours'] * 3600
                if not hasattr(self, 'last_cleanup') or current_time - self.last_cleanup > cleanup_interval:
                    days_to_keep = BOT_SETTINGS['keep_records_days']
                    self.db.cleanup_old_vehicles(days_old=days_to_keep)
                    self.last_cleanup = current_time
                
                # Wait for the next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(self.check_interval)
    
    async def run(self):
        """Run the bot"""
        logger.info("Starting Yad2 Telegram Bot...")
        
        # Start the monitoring loop as a background task
        monitoring_task = asyncio.create_task(self.monitoring_loop())
        
        # Start the Telegram bot
        await self.application.initialize()
        await self.application.start()
        
        # Send startup message if enabled
        if BOT_SETTINGS['enable_startup_message']:
            try:
                bot = Bot(token=self.bot_token)
                enabled_configs = [f"• {c['name']}" for c in self.search_configs]
                startup_msg = f"""🤖 Yad2 Monitor Bot started!

I'll check for new vehicle ads every {self.check_interval} seconds.

Monitoring:
{chr(10).join(enabled_configs)}

Send /start for available commands."""
                await bot.send_message(
                    chat_id=self.chat_id,
                    text=startup_msg
                )
            except Exception as e:
                logger.error(f"Error sending startup message: {str(e)}")
        
        try:
            # Keep the bot running
            await monitoring_task
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.is_monitoring = False
            await self.application.stop()
            await self.application.shutdown()

def main():
    """Main function"""
    try:
        bot = Yad2TelegramBot()
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")

if __name__ == "__main__":
    main()
