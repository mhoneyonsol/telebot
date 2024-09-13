import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler

API_TOKEN = '7413088498:AAHIHrC2jO4DGy0FFa7pX9tNJ8KS-ED89II'

# Setup logging to debug issues
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Handler for the /start command
def start(update, context):
    welcome_message = """
🎉 *Welcome to PixelWar!* 🎉
You're embarking on an exciting adventure on the TON blockchain! 🚀

💰 *Start buying and selling pixels* and join pixel art battles to win TON.

👇 *Select an option below to get started and begin winning*:
    """



    
    keyboard = [
        [InlineKeyboardButton("🎨 Pixel MAP", url='https://t.me/pxltonbot/buypixels')],
        [InlineKeyboardButton("⚔️ Battle Pixel Art", url='https://t.me/pxltonbot/artbattle')],
        [InlineKeyboardButton("👤 Profil", callback_data='profile')],
        [InlineKeyboardButton("🎁 Rewards", callback_data='rewards')],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data='leaderboard')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

# Main function to set up the bot
def main():
    # Create an Updater object with the bot token
    updater = Updater(token=API_TOKEN, use_context=True)

    # Add a handler for the /start command
    updater.dispatcher.add_handler(CommandHandler('start', start))

    # Start polling for updates from Telegram
    updater.start_polling()

    # Block until you press Ctrl+C or the process is terminated
    updater.idle()

if __name__ == '__main__':
    main()
