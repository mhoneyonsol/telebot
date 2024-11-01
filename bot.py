import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

# Load environment variables from .env file
load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")

# Firebase configuration using environment variables from .env file
firebase_config = {
    "type": os.getenv("FIREBASE_TYPE"),
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
    "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN")
}

# Initialize Firebase with the loaded configuration
cred = credentials.Certificate(json.loads(json.dumps(firebase_config)))
firebase_admin.initialize_app(cred)
db = firestore.client()

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Handler for the /start command
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username or update.effective_user.first_name or "Player"
    user_doc_ref = db.collection('users').document(username)
    user_doc = user_doc_ref.get()
    if user_doc.exists:
        user_doc_ref.update({"chat_id": update.effective_chat.id})
    else:
        user_doc_ref.set({"chat_id": update.effective_chat.id})

    welcome_message = f"""
🚀 *Welcome, {username} ! 
 
Step into Pixel WAR*, where the excitement of gaming meets the power of the TON blockchain. 

💸 *Earn Real Rewards*: From daily rewards to seasonal events, there’s always a new way to boost your PXL wallet and dominate the leaderboard. 

🎮 *Endless Fun & Updates*: Dive into a wide range of games with frequent updates to keep the experience fresh and thrilling! 

🔗 *Seamless Wallet Integration*: Connect your TON wallet to track your rewards, manage assets, and unlock real token rewards along with exclusive airdrops. 

In the meantime, don’t forget to invite  friends - it’s more fun together, and you’ll also get a small bonus for bringing them in. 

**Ready to join the battle for PXL?** Start farming, trading, and earning on TON today with Pixel WAR! 
    """
    keyboard = [
        [InlineKeyboardButton("💎 Launcher", url='https://t.me/pxltonbot/home')],
        [InlineKeyboardButton("👤 Profil", callback_data='profile')],
        [InlineKeyboardButton("🎁 Rewards", url='https://t.me/pxltonbot/home#rewards')],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data='leaderboard')],
        [InlineKeyboardButton("📢 Invite Friends", url='https://t.me/share/url?url=https://t.me/pxltonbot')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

# Function to send a message to all users
async def send_update_to_all_users():
    bot = Bot(token=API_TOKEN)
    users_ref = db.collection('users')
    docs = users_ref.stream()

    update_message = "🔔 *Update Alert!* We've made some changes to improve your experience. Our bot will now send you real-time update 😎💙"

    # URL to the WEBP image you want to send
    photo_url = 'https://i.giphy.com/media/v1.Y2lkPTc5MGI3NjExNms1YnR2ZDAyY2VzbzhqYm45NHloam5nNHVseHBlM284Zzd3dGZ0aCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Lopx9eUi34rbq/giphy.gif'

    for doc in docs:
        user_data = doc.to_dict()
        chat_id = user_data.get("chat_id")
        if chat_id:
            try:
                # Send the photo from the URL with the message
                await bot.send_animation(chat_id=chat_id, animation=gif_url, caption=update_message, parse_mode='Markdown')
                logger.info(f"Message sent to chat_id {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send message to chat_id {chat_id}: {e}")



# Command to broadcast message to all users, restricted to admin
async def broadcast(update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username == ADMIN_USERNAME:
        await send_update_to_all_users()
        await update.message.reply_text("Update sent to all users.")
    else:
        await update.message.reply_text("You don't have permission to use this command.")

# Main function to set up the bot
def main():
    application = ApplicationBuilder().token(API_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('broadcast', broadcast))
    
    # Start polling for updates from Telegram
    application.run_polling()

if __name__ == '__main__':
    main()
