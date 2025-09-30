from datetime import datetime
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from telegram.ext import PreCheckoutQueryHandler, MessageHandler, filters

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


# Function to convert a timestamp to a readable format
def convert_timestamp_to_readable(timestamp):
    try:
        if isinstance(timestamp, int):  # Assume it's in milliseconds
            timestamp_seconds = timestamp // 1000
            # Format as `dd-mm-yy, HH:MM`
            return datetime.utcfromtimestamp(timestamp_seconds).strftime('%d-%m-%y, %H:%M')
        else:
            return "Not Available"
    except Exception as e:
        logger.error(f"Error converting timestamp: {e}")
        return "Not Available"



# Handler for the /start command
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Initialize a ThreadPoolExecutor
executor = ThreadPoolExecutor()

# Handler for the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        username = user.username or user.first_name or "Player"
        chat_id = update.effective_chat.id
        user_id = user.id

        # Extraire le code de référence
        referral_code = None
        if context.args and len(context.args) > 0:
            arg = context.args[0]
            if arg.startswith('ref_'):
                referral_code = arg.replace('ref_', '')
                logger.info(f"Referral code detected: {referral_code}")

        logger.info(f"User '{username}' with ID '{user_id}' started the bot.")

        # Save user data in Firestore
        user_doc_ref = db.collection('users').document(username)
        loop = asyncio.get_event_loop()
        user_doc = await loop.run_in_executor(executor, user_doc_ref.get)

        user_data = {
            "chat_id": chat_id,
            "user_id": user_id
        }
        
        if referral_code:
            user_data["pending_referral_code"] = referral_code

        if user_doc.exists:
            await loop.run_in_executor(executor, user_doc_ref.update, user_data)
        else:
            await loop.run_in_executor(executor, user_doc_ref.set, user_data)

        # 🆕 SI CODE DE RÉFÉRENCE → OUVRIR LA WEBAPP DIRECTEMENT
        if referral_code:
            webapp_url = f'https://t.me/nestortonbot/hello?startapp=ref_{referral_code}'
            
            keyboard = [[InlineKeyboardButton("🎮 Launch Game Now", url=webapp_url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            welcome_message = f"""
🎉 *Welcome, {username}!*

You've been invited to join Tokearn! 🚀

Click below to start earning NES tokens right away! 👇
"""
            await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
            return

        # Message normal pour les utilisateurs sans code de référence
        welcome_message = f"""
🚀 *Welcome, {username}!* 

Step into *Tokearn*, where the excitement of gaming meets the power of the TON blockchain.

💸 *Earn Real Rewards*: From daily rewards to seasonal events, there's always a new way to boost your NES wallet and dominate the leaderboard.

🎮 *Endless Fun & Updates*: Dive into a wide range of games with frequent updates to keep the experience fresh and thrilling!

🔗 *Seamless Wallet Integration*: Connect your TON wallet to track your rewards, manage assets, and unlock real token rewards along with exclusive airdrops.

Ready to join the battle for NES? Start farming, trading, and earning on TON today with Nestor LABS!
"""

        keyboard = [
            [InlineKeyboardButton("💎 Launch dApp", url='https://t.me/nestortonbot/hello')],
            [InlineKeyboardButton("👾 Stardust", url='https://t.me/nestortonbot/Stardust')],
            [InlineKeyboardButton("👾 Runner", url='https://t.me/nestortonbot/Runner')],
            [InlineKeyboardButton("👤 Profile", callback_data='profile')],
            [InlineKeyboardButton("🗯️ Channel", url='https://t.me/pxlonton')],
            [InlineKeyboardButton("🎁 Rewards", url='https://t.me/pxltonbot/home#rewards')],
            [InlineKeyboardButton("🏆 Leaderboard", callback_data='leaderboard')],
            [InlineKeyboardButton("📢 Invite Friends", url='https://t.me/share/url?url=https://t.me/nestortonbot')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in /start handler: {e}")
        await update.message.reply_text("An error occurred. Please try again later.")


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
                leaderboard_text += f"🌟 **{rank} - {user}** | 💰 {formatted_balance} NES | Lvl {level}\n"
            elif rank == 1:
                # Highlight the top rank
                leaderboard_text += f"🥇 **{rank} - {user}** | 💰 {formatted_balance} NES | 🏅 Lvl {level}\n"
            else:
                leaderboard_text += f"{rank} - {user} | 💰 {formatted_balance} NES | Lvl {level}\n"

        # Add user's rank at the top
        if user_rank:
            rank_text = f"Your rank is: **#{user_rank}** 🎉\n\n"
        else:
            rank_text = "Your rank is: Not Available 😢\n\n"

        # Add a footer or call-to-action
        footer = "\n🎮 *Keep playing to climb the leaderboard!*"

        # Add a button to launch the app
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏆 View Profile", callback_data='profile')],
            [InlineKeyboardButton("🚀 Launch App", url="https://t.me/nestortonbot/home")]
        ])

        if update.callback_query:
            # If triggered via callback query
            await update.callback_query.answer()

            # Send the animation and leaderboard text in the same new message
            await context.bot.send_animation(
                chat_id=update.effective_chat.id,
                animation="https://i.imgur.com/gdyscr0.gif",
                caption=header + rank_text + leaderboard_text + footer,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            # If triggered via the /leaderboard command
            await context.bot.send_animation(
                chat_id=update.effective_chat.id,
                animation="https://i.imgur.com/gdyscr0.gif",
                caption=header + rank_text + leaderboard_text + footer,
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



# Handler for the /profile command
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username or update.effective_user.first_name
    try:
        # Fetch user data from Firestore
        user_doc_ref = db.collection('users').document(username)
        user_doc = user_doc_ref.get()

        if user_doc.exists:
            user_data = user_doc.to_dict()
            # Extract relevant user information
            claimed_day = user_data.get('claimedDay', 'Not Available')
            last_claim_timestamp = user_data.get('lastClaimTimestamp', 'Not Available')
            last_session_time = user_data.get('last_session_time', 'Not Available')
            level = user_data.get('level_notified', 'Not Available')
            time_on_app = user_data.get('time_on_app', 'Not Available')
            token_balance = user_data.get('token_balance', 0)
            tons_balance = user_data.get('tons_balance', '0')
            wallet_address = user_data.get('wallet_address', 'Not Linked')

            # Convert timestamps to readable format
            last_claim = convert_timestamp_to_readable(last_claim_timestamp)

            # Convert time on app to hours and minutes
            if isinstance(time_on_app, int):
                hours = time_on_app // 3600
                minutes = (time_on_app % 3600) // 60
                time_on_app_formatted = f"{hours}h {minutes}m"
            else:
                time_on_app_formatted = "Not Available"

            # Format the token and TON balances
            formatted_token_balance = format_number(token_balance)
            formatted_ton_balance = f"{tons_balance} TON"

            # Build the profile message
            profile_message = f"""
👤 *Profile Information*

📛 *Username*: `{username}`
📅 *Claimed Days*: `{claimed_day}`
🕒 *Last Claim*: `{last_claim}`
📱 *Last Session*: `{last_session_time}`
🎮 *Level*: `{level}`
⏱️ *Time on App*: `{time_on_app_formatted}`
💰 *Token Balance*: `{formatted_token_balance} NES`
🔹 *TON Balance*: `{formatted_ton_balance}`
💼 *Wallet Address*: `{wallet_address}`

🌟 Every step counts – keep progressing !
            """

            # Inline keyboard for additional actions
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏆 View Leaderboard", callback_data='leaderboard')],
                [InlineKeyboardButton("🚀 Launch App", url="https://t.me/nestortonbot/home")]
            ])

            # Respond with the profile information including the GIF
            if update.callback_query:
                await update.callback_query.answer()
                await context.bot.send_animation(
                    chat_id=update.effective_chat.id,
                    animation="https://i.imgur.com/NqniPEJ.gif",
                    caption=profile_message,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                await context.bot.send_animation(
                    chat_id=update.effective_chat.id,
                    animation="https://i.imgur.com/NqniPEJ.gif",
                    caption=profile_message,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
        else:
            # User document does not exist
            error_message = "❌ No profile information found. Please start using the app to generate your profile!"
            if update.callback_query:
                await update.callback_query.edit_message_text(error_message)
                await update.callback_query.answer()
            else:
                await update.message.reply_text(error_message)

    except Exception as e:
        logger.error(f"Error fetching profile for {username}: {e}")
        error_message = "An error occurred while fetching your profile. Please try again later."
        if update.callback_query:
            await update.callback_query.edit_message_text(error_message)
            await update.callback_query.answer()
        else:
            await update.message.reply_text(error_message)

# Function to send a message to all users
async def send_update_to_all_users():
    bot = Bot(token=API_TOKEN)
    users_ref = db.collection('users')
    docs = users_ref.stream()

    update_message = """🎮 *New Game Alert!* 

🚀 We're excited to announce our brand new Unity game is now available for testing!

🎯 *Runner* - An exciting new gaming experience
👾 Currently in Alpha phase
🔥 Be among the first to try it out!

Your feedback will help us make the game even better! 🌟"""

    # URL to an exciting gaming/launch related gif
    gif_url = 'https://i.imgur.com/ScFz9BY.gif'

    # Inline keyboard with buttons to launch the game and view profile
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Play Runner", url='https://t.me/nestortonbot/Runner')],
        [InlineKeyboardButton("👤 View Profile", callback_data='profile')]
    ])

    for doc in docs:
        user_data = doc.to_dict()
        chat_id = user_data.get("chat_id")
        if chat_id:
            try:
                await bot.send_animation(
                    chat_id=chat_id,
                    animation=gif_url,
                    caption=update_message,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                logger.info(f"New game announcement sent to chat_id {chat_id}")
                # Add a small delay to avoid hitting rate limits
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Failed to send game announcement to chat_id {chat_id}: {e}")


# Command to broadcast message to all users, restricted to admin
async def broadcast(update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username == ADMIN_USERNAME:
        await send_update_to_all_users()
        await update.message.reply_text("Update sent to all users.")
    else:
        await update.message.reply_text("You don't have permission to use this command.")




# Handler for the button callback
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == 'leaderboard':
        await leaderboard(update, context)
    elif query.data == 'profile':
        await profile(update, context)



# Gestionnaire pour les pre-checkout queries (obligatoire)
async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionnaire pour les requêtes de pre-checkout"""
    query = update.pre_checkout_query
    
    # Vérifier la validité du payload
    if query.invoice_payload.startswith('stars_payment_'):
        await query.answer(ok=True)
        logger.info(f"Pre-checkout approved for {query.from_user.username}")
    else:
        await query.answer(ok=False, error_message="Invalid payment payload")
        logger.warning(f"Pre-checkout rejected for {query.from_user.username}")

# Gestionnaire pour les paiements réussis
async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionnaire pour les paiements réussis"""
    payment = update.message.successful_payment
    user = update.effective_user
    
    logger.info(f"Successful payment from {user.username}: {payment.total_amount} XTR")
    
    # Traiter le paiement et accorder les avantages premium
    await update.message.reply_text(
        f"✅ Paiement de {payment.total_amount} ⭐ réussi !\n"
        f"Merci pour votre achat premium 🌟"
    )



# Main function to set up the bot
def main():
    application = ApplicationBuilder().token(API_TOKEN).build()

    # Add command handlers (existants)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('broadcast', broadcast))
    application.add_handler(CommandHandler('leaderboard', leaderboard))
    application.add_handler(CommandHandler('profile', profile))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # NOUVEAUX gestionnaires pour les paiements Stars
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    # Start polling for updates
    application.run_polling()

if __name__ == '__main__':
    main()
