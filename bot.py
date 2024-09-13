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
Vous êtes en avance dans cette aventure sur la blockchain TON \\. 🚀

💰 *Commencez à acheter et vendre des pixels* et participez à des batailles de pixel art pour gagner des TON\\.

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

# Handler for the /buy_pixel command to open the mini-app
async def buy_pixel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    web_app_url = "https://pixelwar-b032d9ebe14e.herokuapp.com/VEROK.html"
    
    # Create a button that opens the web app
    web_app_button = InlineKeyboardButton(
        text="Acheter des pixels",
        web_app=WebAppInfo(url=web_app_url)
    )
    
    # Create a keyboard with the button
    keyboard = [[web_app_button]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send the button to the user
    await update.message.reply_text("Cliquez sur le bouton ci\\-dessous pour acheter des pixels:", reply_markup=reply_markup)

# Fonction principale
def main():
    application = ApplicationBuilder().token(API_TOKEN).build()

    # Log bot start
    logger.info("Bot is starting...")

    # Commandes du bot
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('buy_pixel', buy_pixel))

    # Démarrer le bot
    application.run_polling()

if __name__ == '__main__':
    main()
