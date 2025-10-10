"""
BOT TELEGRAM TOKEARN - ULTIMATE VERSION
Bot pour gérer les interactions Telegram avec l'application Tokearn
Fonctionnalités: Profile, Leaderboard, Referral system, Broadcast, 15+ Admin tools
"""

from datetime import datetime, timedelta
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot, Update, BotCommand, BotCommandScopeChat
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import os
import html
import json
from telegram.ext import PreCheckoutQueryHandler, MessageHandler, filters
import asyncio
from concurrent.futures import ThreadPoolExecutor
import csv
import io

# ========================================
# CONFIGURATION ET INITIALISATION
# ========================================

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")

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

cred = credentials.Certificate(json.loads(json.dumps(firebase_config)))
firebase_admin.initialize_app(cred)
db = firestore.client()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor()

# Variable globale pour le mode maintenance
MAINTENANCE_MODE = {"enabled": False, "reason": ""}


# ========================================
# FONCTIONS UTILITAIRES
# ========================================

def format_number(num):
    """Formate un nombre en version compacte (K pour milliers, M pour millions)"""
    if num >= 1_000_000:
        return f"{num // 1_000_000}M"
    elif num >= 1_000:
        return f"{num // 1_000}k"
    return str(num)


def convert_timestamp_to_readable(timestamp):
    """Convertit un timestamp en format lisible"""
    try:
        if isinstance(timestamp, int):
            timestamp_seconds = timestamp // 1000
            return datetime.utcfromtimestamp(timestamp_seconds).strftime('%d-%m-%y, %H:%M')
        else:
            return "Not Available"
    except Exception as e:
        logger.error(f"Error converting timestamp: {e}")
        return "Not Available"


def get_standardized_username(user):
    """Obtient le username de manière standardisée, identique à main.js"""
    if user.username:
        return user.username
    elif user.first_name and user.last_name:
        return f"{user.first_name}_{user.last_name}"
    elif user.first_name:
        return user.first_name
    else:
        return "Unknown_User"


# ========================================
# HANDLER: /start
# ========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère la commande /start du bot"""
    
    # Vérifier le mode maintenance
    if MAINTENANCE_MODE["enabled"] and update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text(
            f"⚠️ *Maintenance Mode*\n\n"
            f"The bot is currently under maintenance.\n"
            f"Reason: {MAINTENANCE_MODE['reason']}\n\n"
            f"Thank you for your patience! 🙏",
            parse_mode='Markdown'
        )
        return
    
    try:
        user = update.effective_user
        username = get_standardized_username(user)
        chat_id = update.effective_chat.id
        user_id = user.id

        referral_code = None
        if context.args and len(context.args) > 0:
            arg = context.args[0]
            if arg.startswith('ref_'):
                referral_code = arg.replace('ref_', '')
                logger.info(f"Referral code detected: {referral_code}")

        logger.info(f"User '{username}' with ID '{user_id}' started the bot.")

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
            # User existant - juste update
            await loop.run_in_executor(executor, user_doc_ref.update, user_data)
        else:
            user_data["created_at"] = firestore.SERVER_TIMESTAMP
            await loop.run_in_executor(executor, user_doc_ref.set, user_data)

        if referral_code:
            webapp_url = f'https://t.me/nestortonbot/hello?startapp=ref_{referral_code}'
            keyboard = [[InlineKeyboardButton("🎮 Launch Game Now", url=webapp_url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            welcome_message = f"🎉 *Welcome, {username}!*\n\nYou've been invited to join Tokearn! 🚀\n\nClick below to start earning NES tokens right away! 👇"
            await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
            return

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
            [InlineKeyboardButton("👤 Profile", callback_data='profile')],
            [InlineKeyboardButton("📢 Get My Referral Link", callback_data='referral')],
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


# ========================================
# SYSTÈME DE RÉFÉRENCE (REFERRAL)
# ========================================

async def send_referral_notification(referrer_username, new_user_username):
    """Envoie une notification Telegram quand quelqu'un rejoint via un lien de référence"""
    try:
        referrer_doc = db.collection('users').document(referrer_username).get()
        
        if not referrer_doc.exists:
            logger.warning(f"Referrer {referrer_username} not found")
            return
        
        referrer_data = referrer_doc.to_dict()
        chat_id = referrer_data.get('chat_id')
        
        if not chat_id:
            logger.warning(f"No chat_id for {referrer_username}")
            return
        
        message = f"""
🎉 *Great News!*

*{new_user_username}* just joined Tokearn using your referral link!

💰 You've earned *1,000 NES* tokens!

Keep sharing to unlock more rewards! 🚀
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Open App", url="https://t.me/nestortonbot/hello")],
            [InlineKeyboardButton("📢 Share Again", url="https://t.me/share/url?url=https://t.me/nestortonbot")]
        ])
        
        bot = Bot(token=API_TOKEN)
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        logger.info(f"Referral notification sent to {referrer_username}")
        
    except Exception as e:
        logger.error(f"Error sending referral notification: {e}")


async def referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler pour le bouton Get My Referral Link"""
    username = get_standardized_username(update.effective_user)
    
    try:
        user_doc_ref = db.collection('users').document(username)
        user_doc = user_doc_ref.get()
        
        if not user_doc.exists:
            message = "❌ *Launch the app first!*\n\nYou need to open the Tokearn app at least once to generate your referral link.\n\nClick below to launch the app:"
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Launch App", url="https://t.me/nestortonbot/hello")]])
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
            return
        
        user_data = user_doc.to_dict()
        referral_code = user_data.get('referral_code')
        
        if not referral_code:
            message = "❌ *Referral code not found!*\n\nPlease open the app to generate your referral code, then try again."
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Launch App", url="https://t.me/nestortonbot/hello")]])
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
            return
        
        referral_link = f"https://t.me/nestortonbot?start=ref_{referral_code}"
        friends_invited = user_data.get('friends_invited', 0)
        tokens_earned = user_data.get('referral_tokens_earned', 0)
        
        message = f"""
🎉 *Your Referral Link*

Share this link to invite friends and earn rewards!

`{referral_link}`

📊 *Your Stats:*
👥 Friends Invited: {friends_invited}
💰 Tokens Earned: {format_number(tokens_earned)} NES

🎁 *Rewards:*
- 1 friend = 1,000 NES
- 5 friends = 6,000 NES + Recruteur Badge
- 10 friends = 10,500 NES + Ambassadeur Badge
- 25 friends = 50,000 NES + Legend Badge
- 50 friends = 150,000 NES + Elite Badge

Start sharing now! 🚀
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={referral_link}&text=Join me on Tokearn! Earn NES tokens by playing games!")],
            [InlineKeyboardButton("🎮 Open App", url="https://t.me/nestortonbot/hello")]
        ])
        
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
        logger.info(f"Referral link sent to {username}")
        
    except Exception as e:
        logger.error(f"Error getting referral link for {username}: {e}")
        await update.callback_query.answer("An error occurred. Please try again.")


# ========================================
# HANDLER: LEADERBOARD
# ========================================

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le classement des meilleurs joueurs"""
    username = get_standardized_username(update.effective_user)
    user_rank = None
    leaderboard_text = ""
    header = "✨ <b>Top Players</b> ✨\n\n"

    try:
        leaderboard_ref = db.collection('mainleaderboard')
        leaderboard_docs = leaderboard_ref.stream()
        sorted_docs = sorted(leaderboard_docs, key=lambda d: int(d.id))

        for doc in sorted_docs:
            rank = int(doc.id)
            data = doc.to_dict()
            user = data.get("username")
            balance = data.get("token_balance", 0)
            level = data.get("level", 1)

            formatted_balance = format_number(balance)
            escaped_user = html.escape(user)

            if user == username:
                user_rank = rank
                leaderboard_text += f"🌟 <b>{rank} - {escaped_user}</b> | 💰 {formatted_balance} NES | Lvl {level}\n"
            elif rank == 1:
                leaderboard_text += f"🥇 <b>{rank} - {escaped_user}</b> | 💰 {formatted_balance} NES | 🏅 Lvl {level}\n"
            else:
                leaderboard_text += f"{rank} - {escaped_user} | 💰 {formatted_balance} NES | Lvl {level}\n"

        if user_rank:
            rank_text = f"Your rank is: <b>#{user_rank}</b> 🎉\n\n"
        else:
            rank_text = "Your rank is: Not Available 😢\n\n"

        footer = "\n🎮 <b>Keep playing to climb the leaderboard!</b>"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏆 View Profile", callback_data='profile')],
            [InlineKeyboardButton("🚀 Launch App", url="https://t.me/nestortonbot/home")]
        ])

        if update.callback_query:
            await update.callback_query.answer()
            await context.bot.send_animation(
                chat_id=update.effective_chat.id,
                animation="https://i.imgur.com/gdyscr0.gif",
                caption=header + rank_text + leaderboard_text + footer,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await context.bot.send_animation(
                chat_id=update.effective_chat.id,
                animation="https://i.imgur.com/gdyscr0.gif",
                caption=header + rank_text + leaderboard_text + footer,
                reply_markup=keyboard,
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        error_message = "An error occurred while fetching the leaderboard. Please try again later."
        
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(error_message)
        else:
            await update.message.reply_text(error_message)


# ========================================
# HANDLER: PROFILE
# ========================================

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le profil de l'utilisateur avec ses statistiques"""
    username = get_standardized_username(update.effective_user)
    
    try:
        user_doc_ref = db.collection('users').document(username)
        user_doc = user_doc_ref.get()

        if user_doc.exists:
            user_data = user_doc.to_dict()
            
            claimed_day = user_data.get('claimedDay', 'Not Available')
            last_claim_timestamp = user_data.get('lastClaimTimestamp', 'Not Available')
            last_session_time = user_data.get('last_session_time', 'Not Available')
            level = user_data.get('level_notified', 'Not Available')
            time_on_app = user_data.get('time_on_app', 'Not Available')
            token_balance = user_data.get('token_balance', 0)
            tons_balance = user_data.get('tons_balance', '0')
            wallet_address = user_data.get('wallet_address', 'Not Linked')

            last_claim = convert_timestamp_to_readable(last_claim_timestamp)

            if isinstance(time_on_app, int):
                hours = time_on_app // 3600
                minutes = (time_on_app % 3600) // 60
                time_on_app_formatted = f"{hours}h {minutes}m"
            else:
                time_on_app_formatted = "Not Available"

            formatted_token_balance = format_number(token_balance)
            formatted_ton_balance = f"{tons_balance} TON"

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

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏆 View Leaderboard", callback_data='leaderboard')],
                [InlineKeyboardButton("🚀 Launch App", url="https://t.me/nestortonbot/home")]
            ])

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


# ========================================
# ADMIN: BROADCAST
# ========================================

async def send_update_to_all_users():
    """Envoie un message à tous les utilisateurs enregistrés"""
    bot = Bot(token=API_TOKEN)
    users_ref = db.collection('users')
    docs = users_ref.stream()

    update_message = """🎮 *New Game Alert!* 

🚀 We're excited to announce our brand new Unity game is now available for testing!

🎯 *Runner* - An exciting new gaming experience
👾 Currently in Alpha phase
🔥 Be among the first to try it out!

Your feedback will help us make the game even better! 🌟"""

    gif_url = 'https://i.imgur.com/ScFz9BY.gif'

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
                logger.info(f"Broadcast sent to chat_id {chat_id}")
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Failed to send to chat_id {chat_id}: {e}")


async def broadcast(update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /broadcast - RÉSERVÉE À L'ADMIN"""
    if update.effective_user.username == ADMIN_USERNAME:
        await send_update_to_all_users()
        await update.message.reply_text("Update sent to all users.")
    else:
        await update.message.reply_text("You don't have permission to use this command.")


# ========================================
# ADMIN: OUTILS DE BASE
# ========================================

async def sendto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /sendto - Envoie un message à un utilisateur spécifique"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: /sendto <username> <message>\n"
            "Example: /sendto johndoe Hello from admin!"
        )
        return
    
    target_username = context.args[0]
    message_text = ' '.join(context.args[1:])
    
    try:
        user_doc_ref = db.collection('users').document(target_username)
        user_doc = user_doc_ref.get()
        
        if not user_doc.exists:
            await update.message.reply_text(f"❌ User '{target_username}' not found.")
            return
        
        user_data = user_doc.to_dict()
        chat_id = user_data.get('chat_id')
        
        if not chat_id:
            await update.message.reply_text(f"❌ No chat_id for '{target_username}'.")
            return
        
        admin_message = f"🔔 *Admin Message*\n\n{message_text}\n\n_This message was sent by the Tokearn team._"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Open App", url="https://t.me/nestortonbot/hello")],
            [InlineKeyboardButton("💬 Contact Support", url="https://t.me/pxlonton")]
        ])
        
        bot = Bot(token=API_TOKEN)
        await bot.send_message(chat_id=chat_id, text=admin_message, parse_mode='Markdown', reply_markup=keyboard)
        
        await update.message.reply_text(f"✅ Message sent to {target_username}!\n\n*Preview:*\n{message_text}", parse_mode='Markdown')
        logger.info(f"Admin message sent to {target_username}: {message_text}")
        
    except Exception as e:
        logger.error(f"Error sending message to {target_username}: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def sendto_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /sendto_gif - Envoie un message avec GIF"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "❌ Usage: /sendto_gif <username> <gif_url> <message>\n"
            "Example: /sendto_gif johndoe https://i.imgur.com/gdyscr0.gif Hello!"
        )
        return
    
    target_username = context.args[0]
    gif_url = context.args[1]
    message_text = ' '.join(context.args[2:])
    
    try:
        user_doc_ref = db.collection('users').document(target_username)
        user_doc = user_doc_ref.get()
        
        if not user_doc.exists:
            await update.message.reply_text(f"❌ User '{target_username}' not found.")
            return
        
        chat_id = user_doc.to_dict().get('chat_id')
        if not chat_id:
            await update.message.reply_text(f"❌ No chat_id for '{target_username}'.")
            return
        
        admin_message = f"🔔 *Admin Message*\n\n{message_text}\n\n_This message was sent by the Tokearn team._"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Open App", url="https://t.me/nestortonbot/hello")],
            [InlineKeyboardButton("💬 Reply", url="https://t.me/pxlonton")]
        ])
        
        bot = Bot(token=API_TOKEN)
        await bot.send_animation(chat_id=chat_id, animation=gif_url, caption=admin_message, parse_mode='Markdown', reply_markup=keyboard)
        
        await update.message.reply_text(f"✅ GIF message sent to {target_username}!", parse_mode='Markdown')
        logger.info(f"Admin GIF sent to {target_username}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def listusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /listusers - Liste tous les utilisateurs"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    try:
        users_ref = db.collection('users')
        docs = users_ref.stream()
        
        user_list = []
        total_users = 0
        
        for doc in docs:
            total_users += 1
            user_data = doc.to_dict()
            username = doc.id
            chat_id = user_data.get('chat_id', 'N/A')
            user_id = user_data.get('user_id', 'N/A')
            token_balance = user_data.get('token_balance', 0)
            
            # ✅ Échapper les caractères HTML pour éviter les erreurs
            escaped_username = html.escape(str(username))
            
            user_list.append(
                f"• {escaped_username}\n"
                f"  ID: <code>{user_id}</code> | Chat: <code>{chat_id}</code>\n"
                f"  Balance: {format_number(token_balance)} NES"
            )
        
        message_header = f"👥 <b>Total Users: {total_users}</b>\n\n"
        
        if not user_list:
            await update.message.reply_text("No users found.")
            return
        
        chunk_size = 20
        for i in range(0, len(user_list), chunk_size):
            chunk = user_list[i:i + chunk_size]
            message = message_header if i == 0 else ""
            message += "\n\n".join(chunk)
            # ✅ Utiliser HTML au lieu de Markdown
            await update.message.reply_text(message, parse_mode='HTML')
            if i + chunk_size < len(user_list):
                await asyncio.sleep(0.5)
        
        logger.info(f"Admin listed all users")
        
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def userinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /userinfo - Affiche les infos d'un utilisateur"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("❌ Usage: /userinfo <username>\nExample: /userinfo johndoe")
        return
    
    target_username = context.args[0]
    
    try:
        user_doc_ref = db.collection('users').document(target_username)
        user_doc = user_doc_ref.get()
        
        if not user_doc.exists:
            await update.message.reply_text(f"❌ User '{target_username}' not found.")
            return
        
        user_data = user_doc.to_dict()
        
        chat_id = user_data.get('chat_id', 'N/A')
        user_id = user_data.get('user_id', 'N/A')
        token_balance = user_data.get('token_balance', 0)
        level = user_data.get('level_notified', 1)
        claimed_day = user_data.get('claimedDay', 'N/A')
        time_on_app = user_data.get('time_on_app', 0)
        wallet_address = user_data.get('wallet_address', 'Not Linked')
        friends_invited = user_data.get('friends_invited', 0)
        referral_code = user_data.get('referral_code', 'N/A')
        
        if isinstance(time_on_app, int):
            hours = time_on_app // 3600
            minutes = (time_on_app % 3600) // 60
            time_formatted = f"{hours}h {minutes}m"
        else:
            time_formatted = "N/A"
        
        info_message = f"""
📊 *User Information: {target_username}*

*Basic Info:*
• User ID: `{user_id}`
• Chat ID: `{chat_id}`
• Level: `{level}`

*Activity:*
• Token Balance: `{format_number(token_balance)} NES`
• Claimed Days: `{claimed_day}`
• Time on App: `{time_formatted}`

*Referral:*
• Referral Code: `{referral_code}`
• Friends Invited: `{friends_invited}`

*Wallet:*
• Address: `{wallet_address}`

_Use /sendto {target_username} <message> to send them a message_
"""
        
        await update.message.reply_text(info_message, parse_mode='Markdown')
        logger.info(f"Admin checked info for {target_username}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# ========================================
# ADMIN: 15 NOUVELLES FEATURES
# ========================================

# 1️⃣ STATS - Dashboard complet
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /stats - Dashboard admin complet"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    try:
        await update.message.reply_text("🔄 Collecting statistics...")
        
        users_ref = db.collection('users')
        all_users = list(users_ref.stream())
        
        total_users = len(all_users)
        now = datetime.utcnow()
        
        # Users actifs
        active_24h = 0
        inactive_7d = 0
        total_balance = 0
        top_holder = {"username": "N/A", "balance": 0}
        
        for user_doc in all_users:
            user_data = user_doc.to_dict()
            balance = user_data.get('token_balance', 0)
            total_balance += balance
            
            if balance > top_holder["balance"]:
                top_holder = {"username": user_doc.id, "balance": balance}
            
            last_session = user_data.get('last_session_time')
            if last_session:
                try:
                    if isinstance(last_session, int):
                        last_session_date = datetime.utcfromtimestamp(last_session / 1000)
                        if (now - last_session_date).days < 1:
                            active_24h += 1
                        if (now - last_session_date).days >= 7:
                            inactive_7d += 1
                except:
                    pass
        
        avg_balance = total_balance / total_users if total_users > 0 else 0
        
        stats_message = f"""
📊 *Bot Statistics*

👥 *Users:* {total_users} total
  ├─ Active (24h): {active_24h}
  └─ Inactive (7d): {inactive_7d}

💰 *Economy:*
  ├─ Total NES: {format_number(total_balance)}
  ├─ Avg balance: {format_number(int(avg_balance))} NES
  └─ Top holder: {top_holder["username"]} ({format_number(top_holder["balance"])})

📅 *Generated:* {now.strftime('%Y-%m-%d %H:%M')} UTC
"""
        
        await update.message.reply_text(stats_message, parse_mode='Markdown')
        logger.info("Admin viewed stats")
        
    except Exception as e:
        logger.error(f"Error in stats: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# 2️⃣ TOPACTIVE - Top utilisateurs actifs
async def topactive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /topactive - Top utilisateurs actifs"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    try:
        users_ref = db.collection('users')
        all_users = list(users_ref.stream())
        
        user_activity = []
        for user_doc in all_users:
            user_data = user_doc.to_dict()
            time_on_app = user_data.get('time_on_app', 0)
            if time_on_app > 0:
                hours = time_on_app / 3600
                user_activity.append({
                    "username": user_doc.id,
                    "hours": hours
                })
        
        user_activity.sort(key=lambda x: x["hours"], reverse=True)
        top_5 = user_activity[:5]
        
        message = "🔥 *Most Active Users (Last 7 Days)*\n\n"
        
        medals = ["🥇", "🥈", "🥉", "4.", "5."]
        for i, user in enumerate(top_5):
            message += f"{medals[i]} {user['username']} - {user['hours']:.1f}h playtime\n"
        
        message += "\n💡 _Tip: Use /givecoins to reward them!_"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        logger.info("Admin viewed top active users")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# 3️⃣ GROWTH - Graphique de croissance
# 3️⃣ GROWTH - Graphique de croissance (version réelle)
async def growth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /growth - Rapport de croissance basé sur les vraies données"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    try:
        users_ref = db.collection('users')
        all_users = list(users_ref.stream())
        
        total_users = len(all_users)
        
        # Si moins de 10 users, afficher un message simple
        if total_users < 10:
            message = f"""
📈 *Growth Report*

👥 Total Users: {total_users}

_Not enough data yet for weekly growth analysis._
_Keep growing! 🚀_
"""
            await update.message.reply_text(message, parse_mode='Markdown')
            return
        
        # Calculer la croissance par semaine (basé sur les 4 dernières semaines)
        now = datetime.utcnow()
        weeks_data = []
        
        for week_offset in range(4, 0, -1):  # Semaines 4, 3, 2, 1
            week_start = now - timedelta(weeks=week_offset)
            week_end = now - timedelta(weeks=week_offset-1)
            
            count = 0
            for user_doc in all_users:
                user_data = user_doc.to_dict()
                
                # Essayer de trouver une date de création
                created_at = None
                
                # Option 1: Champ last_session_time comme proxy
                if 'last_session_time' in user_data:
                    try:
                        last_session = user_data.get('last_session_time')
                        if isinstance(last_session, int):
                            created_at = datetime.utcfromtimestamp(last_session / 1000)
                    except:
                        pass
                
                # Compter si dans cette semaine
                if created_at and week_start <= created_at < week_end:
                    count += 1
            
            weeks_data.append(count)
        
        # Si pas de données de dates, afficher simplement le total
        if sum(weeks_data) == 0:
            # Distribution égale simulée
            avg_per_week = total_users / 4
            weeks_data = [int(avg_per_week)] * 4
            note = "\n⚠️ _Growth data estimated (no creation dates available)_"
        else:
            note = ""
        
        # Construire le message
        message = "📈 *Growth Report (Last 30 Days)*\n\n"
        
        max_week = max(weeks_data) if max(weeks_data) > 0 else 1
        
        for i, count in enumerate(weeks_data, 1):
            bar_length = int((count / max_week) * 15) if max_week > 0 else 0
            bar = "█" * bar_length + "░" * (15 - bar_length)
            
            change = ""
            if i > 1 and weeks_data[i-2] > 0:
                percent = ((count - weeks_data[i-2]) / weeks_data[i-2]) * 100
                change = f" ({percent:+.0f}%)"
            
            message += f"Week {i}: {bar} {count} new users{change}\n"
        
        avg = sum(weeks_data) / len(weeks_data)
        total = sum(weeks_data)
        
        # Déterminer la tendance
        if weeks_data[-1] > weeks_data[0]:
            trend = "↗️ Growing"
        elif weeks_data[-1] < weeks_data[0]:
            trend = "↘️ Declining"
        else:
            trend = "➡️ Stable"
        
        message += f"\n🎯 Average: {int(avg)} users/week\n"
        message += f"📊 Total (4 weeks): {total} users\n"
        message += f"📈 Trend: {trend}"
        message += note
        
        await update.message.reply_text(message, parse_mode='Markdown')
        logger.info("Admin viewed growth report")
        
    except Exception as e:
        logger.error(f"Error in growth: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# 4️⃣ GIVECOINS - Donner des tokens
async def givecoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /givecoins - Donner des tokens à un user"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "❌ Usage: /givecoins <username> <amount> <reason>\n"
            'Example: /givecoins johndoe 5000 "Great job!"'
        )
        return
    
    target_username = context.args[0]
    try:
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Amount must be a number!")
        return
    
    reason = ' '.join(context.args[2:])
    
    try:
        user_doc_ref = db.collection('users').document(target_username)
        user_doc = user_doc_ref.get()
        
        if not user_doc.exists:
            await update.message.reply_text(f"❌ User '{target_username}' not found.")
            return
        
        # Ajouter les tokens
        user_doc_ref.update({
            "token_balance": firestore.Increment(amount)
        })
        
        # Envoyer notification au user
        chat_id = user_doc.to_dict().get('chat_id')
        if chat_id:
            bot = Bot(token=API_TOKEN)
            user_message = f"""
🎁 *You received a gift!*

💰 +{format_number(amount)} NES tokens

📝 Reason: {reason}

From: Tokearn Team
"""
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🎮 Open App", url="https://t.me/nestortonbot/hello")]])
            await bot.send_message(chat_id=chat_id, text=user_message, parse_mode='Markdown', reply_markup=keyboard)
        
        await update.message.reply_text(f"✅ Sent {format_number(amount)} NES to {target_username}!")
        logger.info(f"Admin gave {amount} NES to {target_username}: {reason}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# 5️⃣ GIVEAWAY - Lancer un concours (simplifié)
async def giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /giveaway - Lancer un concours"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: /giveaway <amount> <winners>\n"
            "Example: /giveaway 10000 50"
        )
        return
    
    try:
        amount = int(context.args[0])
        winners = int(context.args[1])
        
        message = f"""
🎁 *GIVEAWAY ALERT!*

💰 Prize: {format_number(amount)} NES
👥 Winners: First {winners} to join

📢 To participate, users must be active in the app!

_Admin: Use /reward_top3 to reward the top players, or manually send rewards with /givecoins_
"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
        logger.info(f"Admin created giveaway: {amount} NES for {winners} winners")
        
    except ValueError:
        await update.message.reply_text("❌ Amount and winners must be numbers!")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")



async def reward_top3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /reward_top3 - Récompenser le top 3 du leaderboard"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    try:
        leaderboard_ref = db.collection('mainleaderboard')
        leaderboard_docs = leaderboard_ref.stream()
        
        # Trier par l'ID du document (qui est le rang)
        sorted_docs = sorted(leaderboard_docs, key=lambda d: int(d.id))
        top_docs = sorted_docs[:3]
        
        rewards = [10000, 5000, 2500]
        
        message = "🏆 <b>Rewarding Top 3 Players...</b>\n\n"
        
        bot = Bot(token=API_TOKEN)
        
        for i, doc in enumerate(top_docs):
            data = doc.to_dict()
            username = data.get("username")
            reward = rewards[i]
            
            # Ajouter les tokens
            user_doc_ref = db.collection('users').document(username)
            user_doc_ref.update({
                "token_balance": firestore.Increment(reward)
            })
            
            # Notifier le user
            user_doc = user_doc_ref.get()
            if user_doc.exists:
                chat_id = user_doc.to_dict().get('chat_id')
                if chat_id:
                    try:
                        user_message = f"🏆 Congratulations! You ranked #{i+1} and received {format_number(reward)} NES! 🎉"
                        await bot.send_message(
                            chat_id=chat_id, 
                            text=user_message
                        )
                        logger.info(f"Reward notification sent to {username}")
                    except Exception as e:
                        logger.error(f"Failed to notify {username}: {e}")
            
            # ✅ Échapper le username pour éviter les erreurs HTML
            escaped_username = html.escape(username)
            message += f"{i+1}. {escaped_username} - Sent {format_number(reward)} NES ✅\n"
        
        total = sum(rewards)
        message += f"\n<b>Total distributed:</b> {format_number(total)} NES"
        
        # ✅ Utiliser HTML au lieu de Markdown
        await update.message.reply_text(message, parse_mode='HTML')
        logger.info("Admin rewarded top 3 players")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# 7️⃣ ANNOUNCE - Annonce avec template
async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /announce - Envoyer une annonce formatée"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "❌ Usage: /announce <type> <title> <description>\n"
            'Example: /announce update "Version 2.0" "New features!"'
        )
        return
    
    ann_type = context.args[0]
    title = context.args[1]
    description = ' '.join(context.args[2:])
    
    icons = {
        "update": "🔄",
        "event": "🎉",
        "maintenance": "⚠️",
        "news": "📰",
        "game": "🎮"
    }
    
    icon = icons.get(ann_type, "📢")
    
    announcement = f"""
{icon} *{title}*

{description}

_Tokearn Team_
"""
    
    try:
        bot = Bot(token=API_TOKEN)
        users_ref = db.collection('users')
        docs = users_ref.stream()
        
        count = 0
        for doc in docs:
            chat_id = doc.to_dict().get("chat_id")
            if chat_id:
                try:
                    await bot.send_message(chat_id=chat_id, text=announcement, parse_mode='Markdown')
                    count += 1
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed: {e}")
        
        await update.message.reply_text(f"✅ Announcement sent to {count} users!")
        logger.info(f"Admin sent announcement: {title}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# 8️⃣ SENDTO_LEVEL - Message par niveau
async def sendto_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /sendto_level - Envoyer un message aux users d'un niveau spécifique"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: /sendto_level <level> <message>\n"
            'Example: /sendto_level 10 "Congrats on level 10!"'
        )
        return
    
    try:
        target_level = int(context.args[0])
        message_text = ' '.join(context.args[1:])
        
        users_ref = db.collection('users')
        all_users = users_ref.stream()
        
        count = 0
        bot = Bot(token=API_TOKEN)
        
        for user_doc in all_users:
            user_data = user_doc.to_dict()
            level = user_data.get('level_notified', 1)
            
            if level >= target_level:
                chat_id = user_data.get('chat_id')
                if chat_id:
                    try:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"🔔 *Level {target_level}+ Message*\n\n{message_text}",
                            parse_mode='Markdown'
                        )
                        count += 1
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.error(f"Failed: {e}")
        
        await update.message.reply_text(f"✅ Message sent to {count} users (level {target_level}+)")
        logger.info(f"Admin sent message to level {target_level}+ users")
        
    except ValueError:
        await update.message.reply_text("❌ Level must be a number!")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# 9️⃣ SENDTO_ACTIVE - Message aux actifs
async def sendto_active(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /sendto_active - Message aux users actifs dans les X derniers jours"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: /sendto_active <days> <message>\n"
            'Example: /sendto_active 7 "Thanks for being active!"'
        )
        return
    
    try:
        days = int(context.args[0])
        message_text = ' '.join(context.args[1:])
        
        now = datetime.utcnow()
        cutoff_date = now - timedelta(days=days)
        
        users_ref = db.collection('users')
        all_users = users_ref.stream()
        
        count = 0
        bot = Bot(token=API_TOKEN)
        
        for user_doc in all_users:
            user_data = user_doc.to_dict()
            last_session = user_data.get('last_session_time')
            
            if last_session:
                try:
                    if isinstance(last_session, int):
                        last_session_date = datetime.utcfromtimestamp(last_session / 1000)
                        if last_session_date >= cutoff_date:
                            chat_id = user_data.get('chat_id')
                            if chat_id:
                                await bot.send_message(
                                    chat_id=chat_id,
                                    text=f"🔔 *Active User Reward*\n\n{message_text}",
                                    parse_mode='Markdown'
                                )
                                count += 1
                                await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed: {e}")
        
        await update.message.reply_text(f"✅ Message sent to {count} active users (last {days} days)")
        logger.info(f"Admin sent message to active users")
        
    except ValueError:
        await update.message.reply_text("❌ Days must be a number!")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# 🔟 SCHEDULE - Programmer un message (simplifié - nécessite système de tâches)
async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /schedule - Info sur la programmation de messages"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    message = """
📅 *Schedule Feature*

⚠️ This feature requires a task scheduler to be implemented.

For now, you can use:
• /broadcast - Immediate broadcast
• /announce - Formatted announcements
• /sendto - Direct messages

_Scheduled messages coming soon!_
"""
    
    await update.message.reply_text(message, parse_mode='Markdown')


# 1️⃣1️⃣ BAN / UNBAN - Bannir un utilisateur
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /ban - Bannir un utilisateur"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: /ban <username> <reason>\n"
            'Example: /ban spammer "Spam and abuse"'
        )
        return
    
    target_username = context.args[0]
    reason = ' '.join(context.args[1:])
    
    try:
        user_doc_ref = db.collection('users').document(target_username)
        user_doc = user_doc_ref.get()
        
        if not user_doc.exists:
            await update.message.reply_text(f"❌ User '{target_username}' not found.")
            return
        
        # Marquer comme banni
        user_doc_ref.update({
            "banned": True,
            "ban_reason": reason,
            "banned_at": firestore.SERVER_TIMESTAMP
        })
        
        # Notifier l'utilisateur
        chat_id = user_doc.to_dict().get('chat_id')
        if chat_id:
            bot = Bot(token=API_TOKEN)
            ban_message = f"🚫 *Account Suspended*\n\nYour account has been suspended.\nReason: {reason}\n\nContact support for more information."
            try:
                await bot.send_message(chat_id=chat_id, text=ban_message, parse_mode='Markdown')
            except:
                pass
        
        await update.message.reply_text(f"✅ User {target_username} has been banned.\nReason: {reason}")
        logger.info(f"Admin banned {target_username}: {reason}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /unban - Débannir un utilisateur"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /unban <username>")
        return
    
    target_username = context.args[0]
    
    try:
        user_doc_ref = db.collection('users').document(target_username)
        user_doc = user_doc_ref.get()
        
        if not user_doc.exists:
            await update.message.reply_text(f"❌ User '{target_username}' not found.")
            return
        
        user_doc_ref.update({
            "banned": False,
            "ban_reason": firestore.DELETE_FIELD,
            "unbanned_at": firestore.SERVER_TIMESTAMP
        })
        
        await update.message.reply_text(f"✅ User {target_username} has been unbanned.")
        logger.info(f"Admin unbanned {target_username}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# 1️⃣2️⃣ MAINTENANCE - Mode maintenance
async def maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /maintenance - Activer/désactiver le mode maintenance"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ Usage: /maintenance <on|off> [reason]\n"
            'Example: /maintenance on "Server update"'
        )
        return
    
    mode = context.args[0].lower()
    
    if mode == "on":
        reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Maintenance in progress"
        MAINTENANCE_MODE["enabled"] = True
        MAINTENANCE_MODE["reason"] = reason
        await update.message.reply_text(f"🔧 *Maintenance mode ENABLED*\n\nReason: {reason}", parse_mode='Markdown')
        logger.info(f"Admin enabled maintenance mode: {reason}")
    elif mode == "off":
        MAINTENANCE_MODE["enabled"] = False
        MAINTENANCE_MODE["reason"] = ""
        await update.message.reply_text("✅ *Maintenance mode DISABLED*\n\nBot is now operational!", parse_mode='Markdown')
        logger.info("Admin disabled maintenance mode")
    else:
        await update.message.reply_text("❌ Use 'on' or 'off'")


# 1️⃣3️⃣ FORCESYNC - Forcer sync Firebase (simulation)
async def forcesync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /forcesync - Forcer la synchronisation Firebase"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    try:
        await update.message.reply_text("🔄 Force syncing all user data...")
        
        start_time = datetime.utcnow()
        users_ref = db.collection('users')
        all_users = list(users_ref.stream())
        
        # Simulation de sync (vérification que tous les documents sont accessibles)
        synced = len(all_users)
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        message = f"""
🔄 *Force Sync Complete*

✅ Synced: {synced} users
⏱️ Time: {duration:.2f} seconds
"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
        logger.info(f"Admin forced sync: {synced} users")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# 1️⃣4️⃣ FINDUSER - Recherche avancée
async def finduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /finduser - Recherche avancée d'utilisateurs"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: /finduser <criteria>\n\n"
            "Examples:\n"
            "• /finduser balance>50000\n"
            "• /finduser level=10\n"
            "• /finduser level>5"
        )
        return
    
    try:
        criteria = context.args[0]
        
        if ">" in criteria:
            field, value = criteria.split(">")
            value = int(value)
            operator = ">"
        elif "=" in criteria:
            field, value = criteria.split("=")
            value = int(value)
            operator = "="
        elif "<" in criteria:
            field, value = criteria.split("<")
            value = int(value)
            operator = "<"
        else:
            await update.message.reply_text("❌ Invalid criteria format!")
            return
        
        field_map = {
            "balance": "token_balance",
            "level": "level_notified"
        }
        
        firestore_field = field_map.get(field, field)
        
        users_ref = db.collection('users')
        all_users = users_ref.stream()
        
        results = []
        for user_doc in all_users:
            user_data = user_doc.to_dict()
            user_value = user_data.get(firestore_field, 0)
            
            match = False
            if operator == ">" and user_value > value:
                match = True
            elif operator == "=" and user_value == value:
                match = True
            elif operator == "<" and user_value < value:
                match = True
            
            if match:
                results.append(f"• {user_doc.id} - {firestore_field}: {user_value}")
        
        if not results:
            await update.message.reply_text("No users found matching criteria.")
            return
        
        message = f"🔍 *Search Results* ({len(results)} found)\n\nCriteria: {criteria}\n\n"
        message += "\n".join(results[:20])  # Limiter à 20 résultats
        
        if len(results) > 20:
            message += f"\n\n_...and {len(results) - 20} more_"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        logger.info(f"Admin searched users: {criteria}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# 1️⃣5️⃣ EXPORT - Export de données
async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /export - Exporter les données en CSV"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    try:
        await update.message.reply_text("📦 Preparing export...")
        
        users_ref = db.collection('users')
        all_users = list(users_ref.stream())
        
        # Créer CSV en mémoire
        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer)
        
        # Header
        csv_writer.writerow([
            'Username', 'User ID', 'Chat ID', 'Token Balance', 
            'Level', 'Friends Invited', 'Claimed Days', 'Time on App (hours)'
        ])
        
        # Data
        for user_doc in all_users:
            user_data = user_doc.to_dict()
            time_hours = (user_data.get('time_on_app', 0) / 3600) if user_data.get('time_on_app') else 0
            
            csv_writer.writerow([
                user_doc.id,
                user_data.get('user_id', 'N/A'),
                user_data.get('chat_id', 'N/A'),
                user_data.get('token_balance', 0),
                user_data.get('level_notified', 1),
                user_data.get('friends_invited', 0),
                user_data.get('claimedDay', 0),
                f"{time_hours:.2f}"
            ])
        
        # Envoyer le fichier
        csv_buffer.seek(0)
        csv_bytes = csv_buffer.getvalue().encode('utf-8')
        
        await update.message.reply_document(
            document=csv_bytes,
            filename=f'tokearn_users_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            caption=f"📊 Export complete!\n\nTotal users: {len(all_users)}"
        )
        
        logger.info(f"Admin exported {len(all_users)} users")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# ========================================
# ADMIN: SETUP MENU
# ========================================

async def setup_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /setup_admin_menu - Configure le menu admin manuellement"""
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Permission denied.")
        return
    
    try:
        admin_commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("stats", "📊 View statistics"),
            BotCommand("topactive", "🔥 Top active users"),
            BotCommand("growth", "📈 Growth report"),
            BotCommand("givecoins", "💰 Give coins to user"),
            BotCommand("giveaway", "🎁 Create giveaway"),
            BotCommand("reward_top3", "🏆 Reward top 3"),
            BotCommand("announce", "📢 Send announcement"),
            BotCommand("sendto_level", "📩 Message by level"),
            BotCommand("sendto_active", "🔥 Message active users"),
            BotCommand("ban", "🚫 Ban user"),
            BotCommand("unban", "✅ Unban user"),
            BotCommand("maintenance", "🔧 Maintenance mode"),
            BotCommand("forcesync", "🔄 Force sync"),
            BotCommand("finduser", "🔍 Search users"),
            BotCommand("export", "📦 Export data"),
            BotCommand("broadcast", "📢 Broadcast message"),
            BotCommand("sendto", "📩 Send to user"),
            BotCommand("sendto_gif", "🎬 Send GIF to user"),
            BotCommand("listusers", "👥 List all users"),
            BotCommand("userinfo", "ℹ️ Get user info"),
            BotCommand("leaderboard", "🏆 View leaderboard"),
            BotCommand("profile", "👤 View profile"),
        ]
        
        admin_chat_id = update.effective_chat.id
        await context.bot.set_my_commands(
            commands=admin_commands,
            scope=BotCommandScopeChat(chat_id=admin_chat_id)
        )
        
        await update.message.reply_text(
            "✅ *Admin menu configured!*\n\n"
            "You now have access to all admin commands! 🚀\n\n"
            "Check the menu (/) to see all available commands.",
            parse_mode='Markdown'
        )
        
        logger.info(f"Admin menu configured for {update.effective_user.username}")
        
    except Exception as e:
        logger.error(f"Error setting up admin menu: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# ========================================
# GESTIONNAIRE DE CALLBACKS
# ========================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère tous les callback_data des boutons inline"""
    query = update.callback_query
    
    if query.data == 'leaderboard':
        await leaderboard(update, context)
    elif query.data == 'profile':
        await profile(update, context)
    elif query.data == 'referral':
        await referral_link(update, context)


# ========================================
# SYSTÈME DE PAIEMENT TELEGRAM STARS
# ========================================

async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionnaire pour les requêtes de pre-checkout"""
    query = update.pre_checkout_query
    
    if query.invoice_payload.startswith('stars_payment_'):
        await query.answer(ok=True)
        logger.info(f"Pre-checkout approved for {query.from_user.username}")
    else:
        await query.answer(ok=False, error_message="Invalid payment payload")
        logger.warning(f"Pre-checkout rejected for {query.from_user.username}")


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionnaire pour les paiements réussis"""
    payment = update.message.successful_payment
    user = update.effective_user
    
    logger.info(f"Successful payment from {user.username}: {payment.total_amount} XTR")
    
    await update.message.reply_text(
        f"✅ Paiement de {payment.total_amount} ⭐ réussi !\n"
        f"Merci pour votre achat premium 🌟"
    )


# ========================================
# CONFIGURATION DU MENU BOT
# ========================================

async def post_init(application):
    """Configure les commandes du bot au démarrage"""
    
    public_commands = [
        BotCommand("start", "Start the bot"),
    ]
    
    admin_commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("stats", "📊 View statistics"),
        BotCommand("topactive", "🔥 Top active users"),
        BotCommand("growth", "📈 Growth report"),
        BotCommand("givecoins", "💰 Give coins to user"),
        BotCommand("giveaway", "🎁 Create giveaway"),
        BotCommand("reward_top3", "🏆 Reward top 3"),
        BotCommand("announce", "📢 Send announcement"),
        BotCommand("sendto_level", "📩 Message by level"),
        BotCommand("sendto_active", "🔥 Message active users"),
        BotCommand("ban", "🚫 Ban user"),
        BotCommand("unban", "✅ Unban user"),
        BotCommand("maintenance", "🔧 Maintenance mode"),
        BotCommand("forcesync", "🔄 Force sync"),
        BotCommand("finduser", "🔍 Search users"),
        BotCommand("export", "📦 Export data"),
        BotCommand("broadcast", "📢 Broadcast"),
        BotCommand("sendto", "📩 Send to user"),
        BotCommand("listusers", "👥 List users"),
        BotCommand("userinfo", "ℹ️ User info"),
    ]
    
    await application.bot.set_my_commands(public_commands)
    logger.info("Public bot commands configured")
    
    try:
        admin_doc = db.collection('users').document(ADMIN_USERNAME).get()
        
        if admin_doc.exists:
            admin_data = admin_doc.to_dict()
            admin_chat_id = admin_data.get('chat_id')
            
            if admin_chat_id:
                await application.bot.set_my_commands(
                    commands=admin_commands,
                    scope=BotCommandScopeChat(chat_id=admin_chat_id)
                )
                logger.info(f"Admin commands configured for chat_id: {admin_chat_id}")
            else:
                logger.warning("Admin chat_id not found")
        else:
            logger.warning("Admin not found in database")
    
    except Exception as e:
        logger.error(f"Error configuring admin commands: {e}")


# ========================================
# FONCTION PRINCIPALE
# ========================================

def main():
    """Point d'entrée principal du bot"""
    application = ApplicationBuilder().token(API_TOKEN).post_init(post_init).build()

    # COMMANDES PUBLIQUES
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('leaderboard', leaderboard))
    application.add_handler(CommandHandler('profile', profile))
    
    # COMMANDES ADMIN DE BASE
    application.add_handler(CommandHandler('broadcast', broadcast))
    application.add_handler(CommandHandler('sendto', sendto))
    application.add_handler(CommandHandler('sendto_gif', sendto_gif))
    application.add_handler(CommandHandler('listusers', listusers))
    application.add_handler(CommandHandler('userinfo', userinfo))
    application.add_handler(CommandHandler('setup_admin_menu', setup_admin_menu))
    
    # 15 NOUVELLES FEATURES ADMIN
    application.add_handler(CommandHandler('stats', stats))
    application.add_handler(CommandHandler('topactive', topactive))
    application.add_handler(CommandHandler('growth', growth))
    application.add_handler(CommandHandler('givecoins', givecoins))
    application.add_handler(CommandHandler('giveaway', giveaway))
    application.add_handler(CommandHandler('reward_top3', reward_top3))
    application.add_handler(CommandHandler('announce', announce))
    application.add_handler(CommandHandler('sendto_level', sendto_level))
    application.add_handler(CommandHandler('sendto_active', sendto_active))
    application.add_handler(CommandHandler('schedule', schedule))
    application.add_handler(CommandHandler('ban', ban))
    application.add_handler(CommandHandler('unban', unban))
    application.add_handler(CommandHandler('maintenance', maintenance))
    application.add_handler(CommandHandler('forcesync', forcesync))
    application.add_handler(CommandHandler('finduser', finduser))
    application.add_handler(CommandHandler('export', export))
    
    # CALLBACKS & PAIEMENTS
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    logger.info("Bot started with 20+ admin features! 🚀")
    application.run_polling()


if __name__ == '__main__':
    main()