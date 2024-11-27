import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
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
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username or update.effective_user.first_name or "Player"
    chat_id = update.effective_chat.id

    # Save or update user data in Firestore
    user_doc_ref = db.collection('users').document(username)
    user_doc = user_doc_ref.get()
    if user_doc.exists:
        user_doc_ref.update({"chat_id": chat_id})
    else:
        user_doc_ref.set({"chat_id": chat_id})

    welcome_message = f"""
🚀 *Welcome, {username}!*

Step into *Nestor LABS*, where the excitement of gaming meets the power of the TON blockchain.

💸 *Earn Real Rewards*: From daily rewards to seasonal events, there’s always a new way to boost your NES wallet and dominate the leaderboard.

🎮 *Endless Fun & Updates*: Dive into a wide range of games with frequent updates to keep the experience fresh and thrilling!

🔗 *Seamless Wallet Integration*: Connect your TON wallet to track your rewards, manage assets, and unlock real token rewards along with exclusive airdrops.

Ready to join the battle for NES? Start farming, trading, and earning on TON today with Nestor LABS!
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

# Handler for the /leaderboard command
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username or update.effective_user.first_name
    user_rank = None
    leaderboard_text = "🏆 *Leaderboard* 🏆\n\n"

    try:
        # Fetch leaderboard data from Firestore, ordering by document ID
        leaderboard_ref = db.collection('mainleaderboard')
        leaderboard_docs = leaderboard_ref.stream()

        # Sort documents based on their document ID (numeric rank)
        sorted_docs = sorted(leaderboard_docs, key=lambda d: int(d.id))  # Sort by document name as rank

        # Build the leaderboard message
        for doc in sorted_docs:
            rank = int(doc.id)  # Document name is the rank
            data = doc.to_dict()
            user = data.get("username")
            balance = data.get("token_balance", 0)
            level = data.get("level", 1)

            if user == username:
                user_rank = rank

            leaderboard_text += f"#{rank} - {user} | 💰 {balance} NES | 🏅 Level {level}\n"

        # Add user's rank at the top
        if user_rank:
            rank_text = f"Your rank is: #{user_rank}\n\n"
        else:
            rank_text = "Your rank is: Not Available\n\n"

        await update.callback_query.edit_message_text(rank_text + leaderboard_text, parse_mode="Markdown")
        await update.callback_query.answer()
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        await update.callback_query.edit_message_text("An error occurred while fetching the leaderboard. Please try again later.")
        await update.callback_query.answer()

# Handler for the button callback
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == 'leaderboard':
        await leaderboard(update, context)

# Command to broadcast a message to all users
async def send_update_to_all_users():
    bot = Bot(token=API_TOKEN)
    users_ref = db.collection('users')
    docs = users_ref.stream()

    update_message = "🔔 *Update Alert!* We've made some changes to improve your experience 😎"

    gif_url = 'https://i.imgur.com/RPGtlZK.gif'

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Launch App", url="https://t.me/nestortonbot/home")],
    ])

    for doc in docs:
        user_data = doc.to_dict()
        chat_id = user_data.get("chat_id")
        if chat_id:
            try:
                await bot.send_animation(chat_id=chat_id, animation=gif_url, caption=update_message, parse_mode='Markdown', reply_markup=keyboard)
                logger.info(f"Message sent to chat_id {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send message to chat_id {chat_id}: {e}")

# Handler for the /broadcast command
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    application.add_handler(CallbackQueryHandler(button_handler))  # Add callback query handler for buttons
    application.add_handler(CommandHandler('broadcast', broadcast))

    # Start polling for updates
    application.run_polling()

if __name__ == '__main__':
    main()
