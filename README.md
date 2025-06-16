# Yad2 Vehicle Monitor Telegram Bot

This project creates a Telegram bot that monitors Yad2.co.il for new vehicle listings and sends notifications to a specified chat.

## Features

- 🚗 Monitors multiple vehicle models simultaneously
- 🔔 Real-time notifications for new listings  
- 🗄️ PostgreSQL database to prevent duplicate notifications
- 📊 Built-in statistics and status commands
- 🎯 Customizable search filters
- 🔄 Automatic cleanup of old listings

## Setup Instructions

### 1. Prerequisites

- Python 3.8+
- PostgreSQL database
- Telegram Bot Token
- Telegram Chat ID

### 2. Installation

#### Option A: Automated Setup (Recommended)

1. Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the bootstrap script:
```bash
python bootstrap.py
```

The bootstrap script will:
- Create your `.env` file from the template
- Set up the PostgreSQL database and user automatically
- Test the configuration
- Run database migrations

#### Option B: Manual Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create environment file:
Copy `env_example.txt` to `.env` and fill in your configuration:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_or_group_id

# Database Configuration  
DATABASE_URL=postgresql://yad2_user:your_password@localhost:5432/yad2_vehicles

# Bot Configuration
CHECK_INTERVAL_SECONDS=60
```

3. Set up database (if not using bootstrap):
```bash
# Run database migrations
python migrations.py

# Or test the full setup
python setup.py
```

### 3. Getting Telegram Credentials

#### Bot Token:
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` 
3. Follow prompts to create your bot
4. Copy the bot token

#### Chat ID:
1. Add your bot to the desired chat/group
2. Send a test message in the chat
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find your chat ID in the response

### 4. Configure Vehicle Searches

Edit the `search_configs` in `telegram_bot.py`:

```python
self.search_configs = [
    {
        'manufacturer': 17,    # Honda
        'model': 10182,        # Civic  
        'name': 'Honda Civic',
        'max_pages': 5
    },
    {
        'manufacturer': 32,    # Nissan
        'model': 10449,        # Model ID
        'name': 'Nissan Model', 
        'max_pages': 5
    },
    # Add more vehicle configurations...
]
```

## Usage

### Running the Bot

```bash
python telegram_bot.py
```

The bot will:
- Start monitoring configured vehicles every minute
- Send startup notification to your chat
- Respond to commands
- Send formatted notifications for new listings

### Bot Commands

- `/start` - Show welcome message and available commands
- `/status` - Display monitoring status and configured vehicles  
- `/stats` - Show database statistics
- `/test` - Send a test message

### Example Notification

```
🚗 Honda Civic
1.5 VTEC TURBO CVT Sport Plus

💰 Price: ₪89,000
📍 Location: Tel Aviv
📅 Production: 2021-03
🏃 Hand: 1
🛣️ Mileage: 45,000 km (22,500 km/year)

📝 Description:
Beautiful Honda Civic in excellent condition...

🔗 View Ad

#NewAd #HondaCivic
```

## File Structure

```
├── telegram_bot.py      # Main bot application
├── database.py          # PostgreSQL database handler
├── scraper.py          # Yad2 web scraper (existing)
├── yad2_parser.py      # HTML parser (existing)  
├── vehicle_analyzer.py # Dashboard (existing)
├── bootstrap.py        # Automated setup script
├── migrations.py       # Database migration system
├── setup.py           # Configuration testing script
├── requirements.txt    # Python dependencies
├── env_example.txt     # Environment variables template
└── README.md          # This file
```

## Database Schema

The bot creates a `vehicles` table with the following columns:

- `ad_number` (Primary Key) - Unique listing identifier
- `price`, `city` - Basic vehicle info
- `vehicle_data` (JSONB) - All vehicle details in flexible JSON format
- `manufacturer_id`, `model_id` - Search configuration IDs
- `first_seen`, `last_seen` - Tracking timestamps
- `is_sent` - Notification status flag

### Database Migrations

The project includes a migration system for managing schema changes:

```bash
# Run all pending migrations
python migrations.py

# Check migration status
python migrations.py status
```

New migrations can be added to the `migrations.py` file for future schema changes.

## Customization

### Adding New Vehicle Models

1. Find manufacturer and model IDs from Yad2 URLs
2. Add to `search_configs` in `telegram_bot.py`
3. Restart the bot

### Changing Check Frequency

Set `CHECK_INTERVAL_SECONDS` in your `.env` file (minimum recommended: 60 seconds)

### Message Formatting

Modify the `format_vehicle_message()` method in `telegram_bot.py` to customize notification appearance.

## Monitoring and Maintenance

### Log Files
The bot logs all activities. Check console output for:
- New vehicle discoveries
- Database operations  
- Error messages
- Monitoring status

### Database Cleanup
- Old vehicles are automatically removed after 7 days
- Cleanup runs every hour during monitoring

### Error Handling
The bot includes robust error handling:
- Continues monitoring if individual requests fail
- Retries on temporary network issues
- Logs errors for debugging

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Verify PostgreSQL is running
   - Check DATABASE_URL format
   - Ensure database and user exist

2. **Telegram API Errors**  
   - Verify bot token is correct
   - Check chat ID format (should include - for groups)
   - Ensure bot has permission to send messages

3. **No New Vehicles Found**
   - Check if manufacturer/model IDs are correct
   - Verify Yad2 website structure hasn't changed
   - Check rate limiting (increase delays if needed)

4. **Bot Not Responding to Commands**
   - Ensure bot is added to the chat
   - Check that commands start with /
   - Verify bot has message handling permissions

### Getting Help

Check the logs for specific error messages and ensure all dependencies are installed correctly.

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is for educational purposes. Please respect Yad2's terms of service and rate limits.
