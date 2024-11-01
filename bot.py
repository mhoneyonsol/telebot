import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Updater, CommandHandler
import firebase_admin
from firebase_admin import credentials, firestore

API_TOKEN = '7413088498:AAHIHrC2jO4DGy0FFa7pX9tNJ8KS-ED89II'
ADMIN_USERNAME = 'kspr444'  # Your Telegram username for broadcast permissions

# Firebase setup
cred = credentials.Certificate("serviceAccountKey.json")  # Path to Firebase service account key JSON
firebase_admin.initialize_app(cred)
db = firestore.client()

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Handler for the /start command
def start(update, context):
    # Get the user's username or fallback to first name if unavailable
    username = update.effective_user.username or update.effective_user.first_name or "Player"
    
    # Use the username as the document ID in Firestore
    user_doc_ref = db.collection('users').document(username)
    
    # Check if the user document already exists
    user_doc = user_doc_ref.get()
    if user_doc.exists:
        # If document exists, update only the chat_id field
        user_doc_ref.update({"chat_id": update.effective_chat.id})
    else:
        # If document does not exist, create it with only the chat_id field
        user_doc_ref.set({"chat_id": update.effective_chat.id})

    # Welcome message with interactive buttons
    welcome_message = f"""
🚀 *Welcome, {username}! Step into Pixel WAR*, where the excitement of gaming meets the power of the TON blockchain.
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

# Function to send a message to all users
def send_update_to_all_users():
    bot = Bot(token=API_TOKEN)
    users_ref = db.collection('users')
    docs = users_ref.stream()

    update_message = "🔔 *Update Alert!* We've made some changes to improve your experience. Check out the latest version of Pixel WAR!"

    for doc in docs:
        user_data = doc.to_dict()
        chat_id = user_data.get("chat_id")
        if chat_id:
            try:
                bot.send_message(chat_id=chat_id, text=update_message, parse_mode='Markdown')
                logger.info(f"Message sent to chat_id {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send message to chat_id {chat_id}: {e}")

# Command to broadcast message to all users, restricted to admin
def broadcast(update, context):
    if update.effective_user.username == ADMIN_USERNAME:  # Check if user is admin
        send_update_to_all_users()
        update.message.reply_text("Update sent to all users.")
    else:
        update.message.reply_text("You don't have permission to use this command.")

# Main function to set up the bot
def main():
    updater = Updater(token=API_TOKEN, use_context=True)

    # Add command handlers
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('broadcast', broadcast))

    # Start polling for updates from Telegram
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
