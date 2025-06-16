import asyncio
import logging
import os
import time
from datetime import datetime
from typing import List, Dict

from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from dotenv import load_dotenv

# Import our custom modules
from scraper import VehicleScraper
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
        
        configs_text = "\n".join([
            f"• {config['name']} (ID: {config['manufacturer']}-{config['model']})"
            for config in self.search_configs
        ])
        
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
    
    async def check_for_new_vehicles(self):
        """Check for new vehicles for all configured searches"""
        logger.info("Checking for new vehicles...")
        
        for config in self.search_configs:
            try:
                manufacturer = config['manufacturer']
                model = config['model']
                max_pages = config.get('max_pages', 5)
                
                logger.info(f"Checking {config['name']} (manufacturer={manufacturer}, model={model})")
                
                # Create a temporary scraper instance
                scraper = VehicleScraper(
                    output_dir="temp_bot_scraping",
                    manufacturer=manufacturer,
                    model=model
                )
                
                # Fetch first page only for frequent checks
                url = scraper.build_url(1)
                
                # Add delay to avoid hitting rate limits
                time.sleep(BOT_SETTINGS['rate_limit_delay'])
                
                response = scraper.session.get(
                    url,
                    headers=scraper.headers,
                    cookies=scraper.cookies,
                    allow_redirects=True
                )
                response.raise_for_status()
                
                if len(response.content) < 50000 or b'__NEXT_DATA__' not in response.content:
                    logger.warning(f"Response seems invalid for {config['name']}")
                    continue
                
                # Parse the data
                data = yad2_parser.extract_json_from_html(response.content.decode("utf-8"))
                listings_data = data['props']['pageProps']['dehydratedState']['queries'][0]['state']['data']
                
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
