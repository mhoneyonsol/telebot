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

# Helper function to format numbers in compact form
def format_number(num):
    if num >= 1_000_000:  # For 1 million and above
        return f"{num // 1_000_000}M"
    elif num >= 1_000:  # For 1 thousand and above
        return f"{num // 1_000}k"
    return str(num)  # For less than 1 thousand, return as-is

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
# Handler for the /leaderboard command
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username or update.effective_user.first_name
    user_rank = None
    leaderboard_text = "🏆 *Leaderboard* 🏆\n\n"
    
    header = "✨ *Top Players* ✨\n\n"

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

            # Format the balance using the helper function
            formatted_balance = format_number(balance)

            # Highlight the user if they're viewing their rank
            if user == username:
                user_rank = rank
                leaderboard_text += f"🌟 **#{rank} - {user}** | 💰 {formatted_balance} NES | 🏅 Level {level}\n"
            elif rank == 1:
                # Highlight the top rank
                leaderboard_text += f"🥇 **#{rank} - {user}** | 💰 {formatted_balance} NES | 🏅 Level {level}\n"
            else:
                leaderboard_text += f"#{rank} - {user} | 💰 {formatted_balance} NES | 🏅 Level {level}\n"

        # Add user's rank at the top
        if user_rank:
            rank_text = f"Your rank is: **#{user_rank}** 🎉\n\n"
        else:
            rank_text = "Your rank is: Not Available 😢\n\n"

        # Add a footer or call-to-action
        footer = "\n🎮 *Keep playing to climb the leaderboard!*"

        # Add a button to launch the app
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Launch App", url="https://t.me/nestortonbot/home")]
        ])

        if update.callback_query:
            # If triggered via callback query
            await update.callback_query.answer()
            # Send the image and then edit the leaderboard message
            await context.bot.send_animation(
                chat_id=update.effective_chat.id,
                animation="https://i.imgur.com/gdyscr0.gif"
            )
            await update.callback_query.edit_message_text(
                header + rank_text + leaderboard_text + footer,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            # If triggered via the /leaderboard command
            await context.bot.send_animation(
                chat_id=update.effective_chat.id,
                animation="https://i.imgur.com/gdyscr0.gif"
            )
            await update.message.reply_text(
                header + rank_text + leaderboard_text + footer,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        error_message = "An error occurred while fetching the leaderboard. Please try again later."
        if update.callback_query:
            await update.callback_query.edit_message_text(error_message)
            await update.callback_query.answer()
        else:
            await update.message.reply_text(error_message)


# Handler for the button callback
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == 'leaderboard':
        await leaderboard(update, context)

# Main function to set up the bot
def main():
    application = ApplicationBuilder().token(API_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('leaderboard', leaderboard))  # Add command handler for /leaderboard
    application.add_handler(CallbackQueryHandler(button_handler))  # Add callback query handler for buttons

    # Start polling for updates
    application.run_polling()

if __name__ == '__main__':
    main()
