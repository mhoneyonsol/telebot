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
🎉 *Bienvenue dans PixelWar* 🎉
Vous êtes en avance dans cette aventure sur la blockchain TON ! 🚀

💰 *Commencez à acheter et vendre des pixels* et participez à des batailles de pixel art pour gagner des TON.

👇 *Sélectionnez un jeu ci-dessous pour démarrer et commencer à gagner* :
    """


    
    keyboard = [
        [InlineKeyboardButton("🎨 Acheter des pixels", url='https://t.me/pxltonbot/buypixels')],
        [InlineKeyboardButton("⚔️ Battle Pixel Art", url='https://t.me/pxltonbot/artbattle')],
        [InlineKeyboardButton("👤 Voir mon profil", callback_data='profile')],
        [InlineKeyboardButton("🎁 Récompenses", callback_data='rewards')],
        [InlineKeyboardButton("🏆 Classement", callback_data='leaderboard')],
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
