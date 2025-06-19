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
            logger.info(f"Sent notification for vehicle {vehicle['adNumber']}")
        except Exception as e:
            logger.error(f"Error sending notification for vehicle {vehicle['adNumber']}: {str(e)}")
    
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

    async def check_for_new_vehicles(self):
        """Check for new vehicles and send notifications"""
        logger.info("Checking for new vehicles...")
        
        # List of Chrome versions to randomize from
        chrome_versions = ["137.0.0.0", "136.0.0.0", "135.0.0.0", "134.0.0.0"]
        
        for config in self.search_configs:
            try:
                url = config['url']
                max_pages = config.get('max_pages', 5)
                
                logger.info(f"Checking {config['name']} (URL: {url})")
                
                # Add delay to avoid hitting rate limits
                time.sleep(BOT_SETTINGS['rate_limit_delay'])
                
                # Create a session for this request
                session = requests.Session()
                ua = UserAgent()
                
                # Generate random headers for each request
                chrome_version = random.choice(chrome_versions)
                headers = {
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'accept-encoding': 'gzip, deflate, br, zstd',
                    'accept-language': 'en-US,en;q=0.9',
                    'cache-control': 'max-age=0',
                    'dnt': '1',
                    'priority': 'u=0, i',
                    'sec-ch-ua': f'"Chromium";v="{chrome_version.split(".")[0]}", "Not/A)Brand";v="24"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"macOS"',
                    'sec-fetch-dest': 'document',
                    'sec-fetch-mode': 'navigate',
                    'sec-fetch-site': 'same-origin',
                    'sec-fetch-user': '?1',
                    'upgrade-insecure-requests': '1',
                    'user-agent': f'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36'
                }
                
                # Set up cookies
                cookies = {
                    '__ssds': '3',
                    'y2018-2-cohort': '43',
                    'cohortGroup': 'C',
                    'abTestKey': '15',
                    '__uzma': '55da8501-f247-4a91-8a57-19c75987e296',
                    '__uzmb': '1749975893',
                    '__uzme': '6903',
                    '__ssuzjsr3': 'a9be0cd8e',
                    '__uzmaj3': '355eedea-b2ed-4c02-92ec-8dbc842b2fc2',
                    '__uzmbj3': '1749975894',
                    '__uzmlj3': 'tafY2FdZcjkgEC0K5j4s/f7RYtYhe/AhsioVyGyyTis=',
                    'guest_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXlsb2FkIjp7InV1aWQiOiIxMTE3YWYwYS0yNDVlLTQxYzctOTg5Ni1iYzRlNmI2OTVlODcifSwiaWF0IjoxNzQ5OTc1ODk1LCJleHAiOjE3ODE1MzM0OTV9.aPPuJzDg7kGA5oshucuzEeGb99H09sCzdXZKR3Je_Rg',
                    'recommendations-home-category': '{"categoryId":1,"subCategoryId":21}',
                    'ab.storage.deviceId.716d3f2d-2039-4ea6-bd67-0782ecd0770b': 'g%3Ab60a4504-2f28-cdc6-e49b-3afb63388151%7Ce%3Aundefined%7Cc%3A1749975895194%7Cl%3A1750276630445',
                    'ab.storage.sessionId.716d3f2d-2039-4ea6-bd67-0782ecd0770b': 'g%3A1996d7c1-6c54-2a4d-e158-c729f0a26cfb%7Ce%3A1750280714203%7Cc%3A1750276630445%7Cl%3A1750278914203',
                    '__uzmcj3': '2413814212675',
                    '__uzmdj3': '1750278914',
                    '__uzmfj3': '7f60009709b3d1-eafe-4ff9-a1fc-9e818d8e16071749975894222303020158-ec8e9d5c6f4125d4142',
                    '__uzmd': '1750278921',
                    '__uzmc': '5841822693326',
                    '__uzmf': '7f60009709b3d1-eafe-4ff9-a1fc-9e818d8e16071749975893057303028360-8c04c88bb204e1aa226',
                    'uzmx': '7f900054e51021-3353-49b3-8035-06cb5dd2de064-1749975893057303028360-47282bc20cff04dd469'
                }
                
                response = session.get(
                    url,
                    headers=headers,
                    cookies=cookies,
                    allow_redirects=True
                )
                response.raise_for_status()
                
                if len(response.content) < 50000 or b'__NEXT_DATA__' not in response.content:
                    logger.warning(f"Response seems invalid for {config['name']}")
                    self.save_invalid_response(config, response, url)
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
                                # Use the same processing logic as yad2_parser
                                year = vehicle_raw['vehicleDates']['yearOfProduction']
                                month = yad2_parser.get_month_number(
                                    vehicle_raw['vehicleDates'].get('monthOfProduction', {"text": "ינואר"})['text']
                                )
                                production_date = f"{year}-{month:02d}-01"
                                
                                years_since_production = yad2_parser.calculate_years_since_production(year, month)
                                km = vehicle_raw['km']
                                km_per_year = round(km / years_since_production if years_since_production > 0 else km, 2)
                                
                                # Extract HP from subModel text
                                import re
                                hp_match = re.search(r'(\d+)\s*כ״ס', vehicle_raw['subModel']['text'])
                                hp = int(hp_match.group(1)) if hp_match else 0
                                
                                processed_vehicle = {
                                    'adNumber': vehicle_raw['adNumber'],
                                    'price': vehicle_raw['price'],
                                    'city': vehicle_raw['address'].get('city', {"text": ""})['text'],
                                    'adType': vehicle_raw['adType'],
                                    'model': vehicle_raw['model']['text'],
                                    'subModel': vehicle_raw['subModel']['text'],
                                    'hp': hp,
                                    'make': vehicle_raw['manufacturer']['text'],
                                    'productionDate': production_date,
                                    'km': vehicle_raw['km'],
                                    'hand': vehicle_raw['hand']["id"],
                                    'createdAt': yad2_parser.format_date(vehicle_raw['dates']['createdAt']),
                                    'updatedAt': yad2_parser.format_date(vehicle_raw['dates']['updatedAt']),
                                    'rebouncedAt': yad2_parser.format_date(vehicle_raw['dates']['rebouncedAt']),
                                    'listingType': listing_type,
                                    'number_of_years': years_since_production,
                                    'km_per_year': km_per_year,
                                    'description': vehicle_raw["metaData"]["description"],
                                    'link': f'https://www.yad2.co.il/vehicles/item/{vehicle_raw["token"]}',
                                }
                                processed_vehicles.append(processed_vehicle)
                                
                            except Exception as e:
                                logger.error(f"Error processing vehicle: {str(e)}")
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
                        self.db.mark_as_sent([vehicle['adNumber']])
                        
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
