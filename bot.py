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
    # Get the user's username or fallback to first name if unavailable
    username = update.effective_user.username or update.effective_user.first_name or "Player"
    
    # Insert the username in the welcome message
    welcome_message = f"""
🚀 *Welcome, {username}! Step into Pixel WAR*, where the excitement of gaming meets the power of the TON blockchain. Claim, trade, and game to grow your PXL balance, all while exploring a constantly evolving world.

💸 *Earn Real Rewards*: From daily prizes to seasonal events, there’s always a new way to boost your earnings and dominate the leaderboard.

🎮 *Endless Fun & Updates*: Dive into a wide range of games with frequent updates to keep the experience fresh and thrilling!

🔗 *Seamless Wallet Integration*: Connect your TON wallet to track your rewards, manage assets, and unlock real token rewards along with exclusive airdrops.

**Ready to join the battle for pixels?** Start farming, trading, and earning on TON today with Pixel WAR!
    """

    keyboard = [
        [InlineKeyboardButton("💎 Launcher", url='https://t.me/pxltonbot/home')],
        [InlineKeyboardButton("👤 Profil", callback_data='profile')],
        [InlineKeyboardButton("🎁 Rewards", url='https://t.me/pxltonbot/home#rewards')],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data='leaderboard')],
        [InlineKeyboardButton("📢 Invite Friends", url='https://t.me/share/url?url=https://t.me/pxltonbot')],
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
