import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackContext
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
    "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN"),
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
    if user_doc.exists():
        user_doc_ref.update({"chat_id": update.effective_chat.id})
    else:
        user_doc_ref.set({"chat_id": update.effective_chat.id})

    welcome_message = f"""
🚀 *Welcome, {username} ! 
 
Step into Nestor LABS*, where the excitement of gaming meets the power of the TON blockchain. 

💸 *Earn Real Rewards*: From daily rewards to seasonal events, there’s always a new way to boost your NES wallet and dominate the leaderboard. 

🎮 *Endless Fun & Updates*: Dive into a wide range of games with frequent updates to keep the experience fresh and thrilling! 

🔗 *Seamless Wallet Integration*: Connect your TON wallet to track your rewards, manage assets, and unlock real token rewards along with exclusive airdrops. 

In the meantime, don’t forget to invite friends - it’s more fun together, and you’ll also get a small bonus for bringing them in. 

**Ready to join the battle for NES?** Start farming, trading, and earning on TON today with Nestor LABS! 
    """
    keyboard = [
        [InlineKeyboardButton("💎 Launcher", url='https://t.me/nestortonbot/home')],
        [InlineKeyboardButton("👤 Channel", url='https://t.me/pxlonton')],
        [InlineKeyboardButton("🎁 Rewards", url='https://t.me/pxltonbot/home#rewards')],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data='leaderboard')],
        [InlineKeyboardButton("📢 Invite Friends", url='https://t.me/share/url?url=https://t.me/pxltonbot')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

# Function to send the /start command to all users
async def send_start_to_all_users():
    users_ref = db.collection('users')
    docs = users_ref.stream()

    for doc in docs:
        user_data = doc.to_dict()
        chat_id = user_data.get("chat_id")
        if chat_id:
            try:
                # Create a fake update object for each user
                fake_update = Update(
                    update_id=0,
                    message=telegram.Message(
                        message_id=0,
                        date=None,  # Pass a valid date object if needed
                        chat=telegram.Chat(id=chat_id, type="private"),
                        text="/start",
                    ),
                )
                # Create a fake context object
                fake_context = CallbackContext(application=ApplicationBuilder().token(API_TOKEN).build())
                
                # Call the start handler
                await start(fake_update, fake_context)
                
                logger.info(f"/start sent to chat_id {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send /start to chat_id {chat_id}: {e}")

# Command to send /start to all users, restricted to admin
async def broadcast_start(update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username == ADMIN_USERNAME:
        await send_start_to_all_users()
        await update.message.reply_text("Start command sent to all users.")
    else:
        await update.message.reply_text("You don't have permission to use this command.")

# Main function to set up the bot
def main():
    application = ApplicationBuilder().token(API_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('broadcast_start', broadcast_start))
    
    # Start polling for updates from Telegram
    application.run_polling()

if __name__ == '__main__':
    main()
