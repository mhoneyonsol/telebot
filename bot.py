import logging
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_TOKEN = '7413088498:AAHIHrC2jO4DGy0FFa7pX9tNJ8KS-ED89II'

# Setup logging to debug issues
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Handler pour la commande /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = """
🎉 *Bienvenue dans PixelWar* 🎉
Vous êtes en avance dans cette aventure sur la blockchain TON \\! 🚀

💰 *Commencez à acheter et vendre des pixels* et participez à des batailles de pixel art pour gagner des TON.

👇 *Sélectionnez un jeu ci\\-dessous pour démarrer et commencer à gagner* :
    """
    keyboard = [
        [InlineKeyboardButton("🎨 Acheter des pixels", callback_data='buy_pixel')],
        [InlineKeyboardButton("⚔️ Battle Pixel Art", callback_data='pixel_battle')],
        [InlineKeyboardButton("👤 Voir mon profil", callback_data='profile')],
        [InlineKeyboardButton("🎁 Récompenses", callback_data='rewards')],
        [InlineKeyboardButton("🏆 Classement", callback_data='leaderboard')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send the welcome message with inline buttons
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='MarkdownV2')


# Fonction principale
def main():
    application = ApplicationBuilder().token(API_TOKEN).build()

    # Log bot start
    logger.info("Bot is starting...")

    # Commandes du bot
    application.add_handler(CommandHandler('start', start))

    # Démarrer le bot
    application.run_polling()

if __name__ == '__main__':
    main()
