"""
BOT TELEGRAM TOKEARN
Bot pour gérer les interactions Telegram avec l'application Tokearn
Fonctionnalités: Profile, Leaderboard, Referral system, Broadcast, Admin tools
"""

from datetime import datetime
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot, Update, BotCommand, BotCommandScopeChat
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import os
import html  # Pour échapper les caractères HTML dans les usernames
import json
from telegram.ext import PreCheckoutQueryHandler, MessageHandler, filters
import asyncio
from concurrent.futures import ThreadPoolExecutor

# ========================================
# CONFIGURATION ET INITIALISATION
# ========================================

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Récupérer les tokens et identifiants depuis les variables d'environnement
API_TOKEN = os.getenv("API_TOKEN")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")

# Configuration Firebase depuis les variables d'environnement
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

# Initialiser Firebase avec les credentials
cred = credentials.Certificate(json.loads(json.dumps(firebase_config)))
firebase_admin.initialize_app(cred)
db = firestore.client()

# Configuration du système de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialiser un ThreadPoolExecutor pour les opérations Firestore asynchrones
executor = ThreadPoolExecutor()


# ========================================
# FONCTIONS UTILITAIRES
# ========================================

def format_number(num):
    """
    Formate un nombre en version compacte (K pour milliers, M pour millions)
    Ex: 1500 -> 1k, 1500000 -> 1M
    """
    if num >= 1_000_000:  # Pour 1 million et plus
        return f"{num // 1_000_000}M"
    elif num >= 1_000:  # Pour 1 millier et plus
        return f"{num // 1_000}k"
    return str(num)  # Moins de 1 millier, retourner tel quel


def convert_timestamp_to_readable(timestamp):
    """
    Convertit un timestamp en format lisible
    Ex: 1699564800000 -> "09-11-23, 14:20"
    """
    try:
        if isinstance(timestamp, int):  # Si c'est en millisecondes
            timestamp_seconds = timestamp // 1000
            # Format: jour-mois-année, heure:minute
            return datetime.utcfromtimestamp(timestamp_seconds).strftime('%d-%m-%y, %H:%M')
        else:
            return "Not Available"
    except Exception as e:
        logger.error(f"Error converting timestamp: {e}")
        return "Not Available"


def get_standardized_username(user):
    """
    Obtient le username de manière standardisée, identique à main.js
    Ceci garantit la cohérence entre le bot et l'application web
    
    Priorité:
    1. Username Telegram (@username)
    2. Prénom + Nom (First_Last)
    3. Prénom seul (First)
    4. "Unknown_User" en dernier recours
    """
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
    """
    Gère la commande /start du bot
    - Enregistre l'utilisateur dans Firebase
    - Gère les codes de référence (referral)
    - Affiche le message de bienvenue avec les boutons
    """
    try:
        user = update.effective_user
        username = get_standardized_username(user)  # Standardiser le username
        chat_id = update.effective_chat.id
        user_id = user.id

        # Vérifier si un code de référence est présent dans la commande
        # Format: /start ref_ABC123
        referral_code = None
        if context.args and len(context.args) > 0:
            arg = context.args[0]
            if arg.startswith('ref_'):
                referral_code = arg.replace('ref_', '')
                logger.info(f"Referral code detected: {referral_code}")

        logger.info(f"User '{username}' with ID '{user_id}' started the bot.")

        # Sauvegarder/Mettre à jour les données utilisateur dans Firestore
        user_doc_ref = db.collection('users').document(username)
        loop = asyncio.get_event_loop()
        user_doc = await loop.run_in_executor(executor, user_doc_ref.get)

        # Données à sauvegarder
        user_data = {
            "chat_id": chat_id,
            "user_id": user_id
        }
        
        # Ajouter le code de référence en attente si présent
        if referral_code:
            user_data["pending_referral_code"] = referral_code

        # Mise à jour ou création du document utilisateur
        if user_doc.exists:
            await loop.run_in_executor(executor, user_doc_ref.update, user_data)
        else:
            await loop.run_in_executor(executor, user_doc_ref.set, user_data)

        # Si code de référence présent, rediriger directement vers l'app
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

        # Message de bienvenue standard pour les utilisateurs sans référence
        welcome_message = f"""
🚀 *Welcome, {username}!* 

Step into *Tokearn*, where the excitement of gaming meets the power of the TON blockchain.

💸 *Earn Real Rewards*: From daily rewards to seasonal events, there's always a new way to boost your NES wallet and dominate the leaderboard.

🎮 *Endless Fun & Updates*: Dive into a wide range of games with frequent updates to keep the experience fresh and thrilling!

🔗 *Seamless Wallet Integration*: Connect your TON wallet to track your rewards, manage assets, and unlock real token rewards along with exclusive airdrops.

Ready to join the battle for NES? Start farming, trading, and earning on TON today with Nestor LABS!
"""

        # Clavier inline avec tous les boutons d'actions
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
    """
    Envoie une notification Telegram quand quelqu'un rejoint via un lien de référence
    Appelée depuis l'API Flask (api.py)
    """
    try:
        # Récupérer le chat_id du parrain (referrer)
        referrer_doc = db.collection('users').document(referrer_username).get()
        
        if not referrer_doc.exists:
            logger.warning(f"Referrer {referrer_username} not found")
            return
        
        referrer_data = referrer_doc.to_dict()
        chat_id = referrer_data.get('chat_id')
        
        if not chat_id:
            logger.warning(f"No chat_id for {referrer_username}")
            return
        
        # Message de notification
        message = f"""
🎉 *Great News!*

*{new_user_username}* just joined Tokearn using your referral link!

💰 You've earned *1,000 NES* tokens!

Keep sharing to unlock more rewards! 🚀
"""
        
        # Boutons d'action
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Open App", url="https://t.me/nestortonbot/hello")],
            [InlineKeyboardButton("📢 Share Again", url="https://t.me/share/url?url=https://t.me/nestortonbot")]
        ])
        
        # Envoyer la notification
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
    """
    Handler pour le bouton "Get My Referral Link"
    Affiche le lien de parrainage de l'utilisateur et ses statistiques
    """
    username = get_standardized_username(update.effective_user)
    
    try:
        # Récupérer les données utilisateur depuis Firestore
        user_doc_ref = db.collection('users').document(username)
        user_doc = user_doc_ref.get()
        
        # Si l'utilisateur n'a pas encore lancé l'app
        if not user_doc.exists:
            message = """
❌ *Launch the app first!*

You need to open the Tokearn app at least once to generate your referral link.

Click below to launch the app:
"""
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Launch App", url="https://t.me/nestortonbot/hello")]
            ])
            
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return
        
        user_data = user_doc.to_dict()
        referral_code = user_data.get('referral_code')
        
        # Si le code de référence n'existe pas encore
        if not referral_code:
            message = """
❌ *Referral code not found!*

Please open the app to generate your referral code, then try again.
"""
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Launch App", url="https://t.me/nestortonbot/hello")]
            ])
            
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            return
        
        # Générer le lien de parrainage
        referral_link = f"https://t.me/nestortonbot?start=ref_{referral_code}"
        
        # Récupérer les statistiques de parrainage
        friends_invited = user_data.get('friends_invited', 0)
        tokens_earned = user_data.get('referral_tokens_earned', 0)
        
        # Message avec le lien et les stats
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
        
        # Boutons pour partager et ouvrir l'app
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={referral_link}&text=Join me on Tokearn! Earn NES tokens by playing games!")],
            [InlineKeyboardButton("🎮 Open App", url="https://t.me/nestortonbot/hello")]
        ])
        
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        logger.info(f"Referral link sent to {username}")
        
    except Exception as e:
        logger.error(f"Error getting referral link for {username}: {e}")
        await update.callback_query.answer("An error occurred. Please try again.")


# ========================================
# HANDLER: LEADERBOARD
# ========================================

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Affiche le classement des meilleurs joueurs
    - Récupère les données depuis la collection 'mainleaderboard'
    - Trie par rang (document ID)
    - Highlight le rang de l'utilisateur courant
    - Utilise HTML pour éviter les problèmes de parsing avec les usernames
    """
    username = get_standardized_username(update.effective_user)
    user_rank = None
    leaderboard_text = ""
    
    header = "✨ <b>Top Players</b> ✨\n\n"

    try:
        # Récupérer les données du leaderboard depuis Firestore
        leaderboard_ref = db.collection('mainleaderboard')
        leaderboard_docs = leaderboard_ref.stream()

        # Trier les documents par leur ID (qui correspond au rang)
        sorted_docs = sorted(leaderboard_docs, key=lambda d: int(d.id))

        # Construire le message du leaderboard
        for doc in sorted_docs:
            rank = int(doc.id)  # L'ID du document = rang
            data = doc.to_dict()
            user = data.get("username")
            balance = data.get("token_balance", 0)
            level = data.get("level", 1)

            # Formater le solde en version compacte (K/M)
            formatted_balance = format_number(balance)
            
            # Échapper les caractères HTML spéciaux dans le username
            # IMPORTANT: évite les erreurs de parsing
            escaped_user = html.escape(user)

            # Mettre en évidence l'utilisateur actuel
            if user == username:
                user_rank = rank
                leaderboard_text += f"🌟 <b>{rank} - {escaped_user}</b> | 💰 {formatted_balance} NES | Lvl {level}\n"
            elif rank == 1:
                # Mettre en évidence le premier rang
                leaderboard_text += f"🥇 <b>{rank} - {escaped_user}</b> | 💰 {formatted_balance} NES | 🏅 Lvl {level}\n"
            else:
                leaderboard_text += f"{rank} - {escaped_user} | 💰 {formatted_balance} NES | Lvl {level}\n"

        # Ajouter le rang de l'utilisateur en haut
        if user_rank:
            rank_text = f"Your rank is: <b>#{user_rank}</b> 🎉\n\n"
        else:
            rank_text = "Your rank is: Not Available 😢\n\n"

        # Footer avec appel à l'action
        footer = "\n🎮 <b>Keep playing to climb the leaderboard!</b>"

        # Boutons d'action
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏆 View Profile", callback_data='profile')],
            [InlineKeyboardButton("🚀 Launch App", url="https://t.me/nestortonbot/home")]
        ])

        # Envoyer le message avec GIF
        if update.callback_query:
            # Si appelé via un bouton callback
            await update.callback_query.answer()
            await context.bot.send_animation(
                chat_id=update.effective_chat.id,
                animation="https://i.imgur.com/gdyscr0.gif",
                caption=header + rank_text + leaderboard_text + footer,
                reply_markup=keyboard,
                parse_mode="HTML"  # Utiliser HTML au lieu de Markdown pour plus de stabilité
            )
        else:
            # Si appelé via la commande /leaderboard
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
    """
    Affiche le profil de l'utilisateur avec ses statistiques
    - Token balance
    - Level
    - Jours de connexion
    - Temps passé sur l'app
    - Wallet address
    """
    username = get_standardized_username(update.effective_user)
    
    try:
        # Récupérer les données utilisateur depuis Firestore
        user_doc_ref = db.collection('users').document(username)
        user_doc = user_doc_ref.get()

        if user_doc.exists:
            user_data = user_doc.to_dict()
            
            # Extraire les informations pertinentes
            claimed_day = user_data.get('claimedDay', 'Not Available')
            last_claim_timestamp = user_data.get('lastClaimTimestamp', 'Not Available')
            last_session_time = user_data.get('last_session_time', 'Not Available')
            level = user_data.get('level_notified', 'Not Available')
            time_on_app = user_data.get('time_on_app', 'Not Available')
            token_balance = user_data.get('token_balance', 0)
            tons_balance = user_data.get('tons_balance', '0')
            wallet_address = user_data.get('wallet_address', 'Not Linked')

            # Convertir les timestamps en format lisible
            last_claim = convert_timestamp_to_readable(last_claim_timestamp)

            # Convertir le temps sur l'app en heures et minutes
            if isinstance(time_on_app, int):
                hours = time_on_app // 3600
                minutes = (time_on_app % 3600) // 60
                time_on_app_formatted = f"{hours}h {minutes}m"
            else:
                time_on_app_formatted = "Not Available"

            # Formater les soldes
            formatted_token_balance = format_number(token_balance)
            formatted_ton_balance = f"{tons_balance} TON"

            # Construire le message du profil
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

            # Boutons d'action
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏆 View Leaderboard", callback_data='leaderboard')],
                [InlineKeyboardButton("🚀 Launch App", url="https://t.me/nestortonbot/home")]
            ])

            # Envoyer le profil avec GIF
            if update.callback_query:
                # Si appelé via un bouton callback
                await update.callback_query.answer()
                await context.bot.send_animation(
                    chat_id=update.effective_chat.id,
                    animation="https://i.imgur.com/NqniPEJ.gif",
                    caption=profile_message,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                # Si appelé via la commande /profile
                await context.bot.send_animation(
                    chat_id=update.effective_chat.id,
                    animation="https://i.imgur.com/NqniPEJ.gif",
                    caption=profile_message,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
        else:
            # Document utilisateur inexistant
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
# SYSTÈME DE BROADCAST (ADMIN UNIQUEMENT)
# ========================================

async def send_update_to_all_users():
    """
    Envoie un message à tous les utilisateurs enregistrés
    Utilisé pour les annonces importantes (nouveaux jeux, mises à jour, etc.)
    """
    bot = Bot(token=API_TOKEN)
    users_ref = db.collection('users')
    docs = users_ref.stream()

    # Message à broadcaster (à personnaliser selon les besoins)
    update_message = """🎮 *New Game Alert!* 

🚀 We're excited to announce our brand new Unity game is now available for testing!

🎯 *Runner* - An exciting new gaming experience
👾 Currently in Alpha phase
🔥 Be among the first to try it out!

Your feedback will help us make the game even better! 🌟"""

    # GIF pour rendre le message plus attractif
    gif_url = 'https://i.imgur.com/ScFz9BY.gif'

    # Boutons d'action
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Play Runner", url='https://t.me/nestortonbot/Runner')],
        [InlineKeyboardButton("👤 View Profile", callback_data='profile')]
    ])

    # Envoyer à tous les utilisateurs
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
                # Délai pour éviter les limites de taux de Telegram
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Failed to send game announcement to chat_id {chat_id}: {e}")


async def broadcast(update, context: ContextTypes.DEFAULT_TYPE):
    """
    Commande /broadcast - RÉSERVÉE À L'ADMIN
    Envoie un message à tous les utilisateurs
    """
    # Vérifier que l'utilisateur est bien l'admin
    if update.effective_user.username == ADMIN_USERNAME:
        await send_update_to_all_users()
        await update.message.reply_text("Update sent to all users.")
    else:
        await update.message.reply_text("You don't have permission to use this command.")


# ========================================
# ADMIN: ENVOYER MESSAGE À UN USER SPÉCIFIQUE
# ========================================

async def sendto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Commande /sendto - RÉSERVÉE À L'ADMIN
    Envoie un message à un utilisateur spécifique
    
    Usage: /sendto username Votre message ici
    Exemple: /sendto johndoe Hello! This is a test message from admin
    """
    
    # Vérifier que l'utilisateur est bien l'admin
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    # Vérifier que la commande contient au moins 2 arguments (username + message)
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: /sendto <username> <message>\n"
            "Example: /sendto johndoe Hello from admin!"
        )
        return
    
    # Extraire le username cible (premier argument)
    target_username = context.args[0]
    
    # Extraire le message (tous les arguments après le username)
    message_text = ' '.join(context.args[1:])
    
    try:
        # Récupérer les données de l'utilisateur cible depuis Firestore
        user_doc_ref = db.collection('users').document(target_username)
        user_doc = user_doc_ref.get()
        
        if not user_doc.exists:
            await update.message.reply_text(
                f"❌ User '{target_username}' not found in database.\n"
                f"Make sure the username is correct and the user has used /start before."
            )
            return
        
        user_data = user_doc.to_dict()
        chat_id = user_data.get('chat_id')
        
        if not chat_id:
            await update.message.reply_text(
                f"❌ No chat_id found for user '{target_username}'.\n"
                f"The user may need to restart the bot with /start."
            )
            return
        
        # Créer le message avec un badge "Admin Message"
        admin_message = f"""
🔔 *Admin Message*

{message_text}

_This message was sent by the Tokearn team._
"""
        
        # Optionnel: Ajouter des boutons d'action
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Open App", url="https://t.me/nestortonbot/hello")],
            [InlineKeyboardButton("💬 Contact Support", url="https://t.me/pxlonton")]
        ])
        
        # Envoyer le message à l'utilisateur cible
        bot = Bot(token=API_TOKEN)
        await bot.send_message(
            chat_id=chat_id,
            text=admin_message,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        # Confirmer à l'admin que le message a été envoyé
        await update.message.reply_text(
            f"✅ Message successfully sent to {target_username}!\n\n"
            f"*Preview:*\n{message_text}",
            parse_mode='Markdown'
        )
        
        logger.info(f"Admin message sent to {target_username}: {message_text}")
        
    except Exception as e:
        logger.error(f"Error sending message to {target_username}: {e}")
        await update.message.reply_text(
            f"❌ Error sending message to {target_username}.\n"
            f"Error: {str(e)}"
        )


# ========================================
# ADMIN: ENVOYER MESSAGE AVEC GIF
# ========================================

async def sendto_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Commande /sendto_gif - RÉSERVÉE À L'ADMIN
    Envoie un message avec GIF à un utilisateur spécifique
    
    Usage: /sendto_gif username <gif_url> Votre message ici
    Exemple: /sendto_gif johndoe https://i.imgur.com/example.gif Check this out!
    """
    
    # Vérifier que l'utilisateur est bien l'admin
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    # Vérifier que la commande contient au moins 3 arguments (username + gif_url + message)
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "❌ Usage: /sendto_gif <username> <gif_url> <message>\n"
            "Example: /sendto_gif johndoe https://i.imgur.com/gdyscr0.gif Hello!"
        )
        return
    
    # Extraire les paramètres
    target_username = context.args[0]
    gif_url = context.args[1]
    message_text = ' '.join(context.args[2:])
    
    try:
        # Récupérer les données de l'utilisateur cible
        user_doc_ref = db.collection('users').document(target_username)
        user_doc = user_doc_ref.get()
        
        if not user_doc.exists:
            await update.message.reply_text(f"❌ User '{target_username}' not found.")
            return
        
        user_data = user_doc.to_dict()
        chat_id = user_data.get('chat_id')
        
        if not chat_id:
            await update.message.reply_text(f"❌ No chat_id found for '{target_username}'.")
            return
        
        # Message avec badge admin
        admin_message = f"""
🔔 *Admin Message*

{message_text}

_This message was sent by the Tokearn team._
"""
        
        # Boutons d'action
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Open App", url="https://t.me/nestortonbot/hello")],
            [InlineKeyboardButton("💬 Reply", url="https://t.me/pxlonton")]
        ])
        
        # Envoyer avec GIF
        bot = Bot(token=API_TOKEN)
        await bot.send_animation(
            chat_id=chat_id,
            animation=gif_url,
            caption=admin_message,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        # Confirmer à l'admin
        await update.message.reply_text(
            f"✅ Message with GIF sent to {target_username}!\n\n"
            f"*GIF:* {gif_url}\n"
            f"*Message:* {message_text}",
            parse_mode='Markdown'
        )
        
        logger.info(f"Admin GIF message sent to {target_username}")
        
    except Exception as e:
        logger.error(f"Error sending GIF to {target_username}: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# ========================================
# ADMIN: LISTER TOUS LES USERS
# ========================================

async def listusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Commande /listusers - RÉSERVÉE À L'ADMIN
    Liste tous les utilisateurs enregistrés dans la base de données
    Affiche: username, chat_id, user_id, token balance
    """
    
    # Vérifier que l'utilisateur est bien l'admin
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    try:
        # Récupérer tous les utilisateurs
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
            
            # Formater la ligne pour cet utilisateur
            user_list.append(
                f"• {username}\n"
                f"  ID: `{user_id}` | Chat: `{chat_id}`\n"
                f"  Balance: {format_number(token_balance)} NES"
            )
        
        # Diviser la liste si trop longue (limite Telegram: 4096 caractères)
        message_header = f"👥 *Total Users: {total_users}*\n\n"
        
        if not user_list:
            await update.message.reply_text("No users found in database.")
            return
        
        # Envoyer par blocs de 20 utilisateurs pour éviter la limite de caractères
        chunk_size = 20
        for i in range(0, len(user_list), chunk_size):
            chunk = user_list[i:i + chunk_size]
            message = message_header if i == 0 else ""
            message += "\n\n".join(chunk)
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
            # Petit délai entre les messages pour éviter les rate limits
            if i + chunk_size < len(user_list):
                await asyncio.sleep(0.5)
        
        logger.info(f"Admin {update.effective_user.username} listed all users")
        
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        await update.message.reply_text(f"❌ Error listing users: {str(e)}")


# ========================================
# ADMIN: OBTENIR INFO D'UN USER SPÉCIFIQUE
# ========================================

async def userinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Commande /userinfo - RÉSERVÉE À L'ADMIN
    Affiche les informations détaillées d'un utilisateur
    
    Usage: /userinfo <username>
    Exemple: /userinfo johndoe
    """
    
    # Vérifier que l'utilisateur est bien l'admin
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    # Vérifier qu'un username est fourni
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "❌ Usage: /userinfo <username>\n"
            "Example: /userinfo johndoe"
        )
        return
    
    target_username = context.args[0]
    
    try:
        # Récupérer les données de l'utilisateur
        user_doc_ref = db.collection('users').document(target_username)
        user_doc = user_doc_ref.get()
        
        if not user_doc.exists:
            await update.message.reply_text(f"❌ User '{target_username}' not found.")
            return
        
        user_data = user_doc.to_dict()
        
        # Extraire toutes les infos disponibles
        chat_id = user_data.get('chat_id', 'N/A')
        user_id = user_data.get('user_id', 'N/A')
        token_balance = user_data.get('token_balance', 0)
        level = user_data.get('level_notified', 1)
        claimed_day = user_data.get('claimedDay', 'N/A')
        time_on_app = user_data.get('time_on_app', 0)
        wallet_address = user_data.get('wallet_address', 'Not Linked')
        friends_invited = user_data.get('friends_invited', 0)
        referral_code = user_data.get('referral_code', 'N/A')
        
        # Formater le temps sur l'app
        if isinstance(time_on_app, int):
            hours = time_on_app // 3600
            minutes = (time_on_app % 3600) // 60
            time_formatted = f"{hours}h {minutes}m"
        else:
            time_formatted = "N/A"
        
        # Construire le message d'info
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
        
        logger.info(f"Admin {update.effective_user.username} checked info for {target_username}")
        
    except Exception as e:
        logger.error(f"Error getting user info for {target_username}: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")


# ========================================
# GESTIONNAIRE DE CALLBACKS
# ========================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Gère tous les callback_data des boutons inline
    - 'leaderboard' -> affiche le classement
    - 'profile' -> affiche le profil
    - 'referral' -> affiche le lien de parrainage
    """
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
    """
    Gestionnaire pour les requêtes de pre-checkout (avant paiement)
    Vérifie que le payload est valide avant d'accepter le paiement
    """
    query = update.pre_checkout_query
    
    # Vérifier la validité du payload
    if query.invoice_payload.startswith('stars_payment_'):
        await query.answer(ok=True)
        logger.info(f"Pre-checkout approved for {query.from_user.username}")
    else:
        await query.answer(ok=False, error_message="Invalid payment payload")
        logger.warning(f"Pre-checkout rejected for {query.from_user.username}")


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Gestionnaire pour les paiements réussis
    Appelé automatiquement après un paiement Telegram Stars confirmé
    """
    payment = update.message.successful_payment
    user = update.effective_user
    
    logger.info(f"Successful payment from {user.username}: {payment.total_amount} XTR")
    
    # Traiter le paiement et accorder les avantages premium
    await update.message.reply_text(
        f"✅ Paiement de {payment.total_amount} ⭐ réussi !\n"
        f"Merci pour votre achat premium 🌟"
    )


# ========================================
# CONFIGURATION DU MENU BOT
# ========================================

async def post_init(application):
    """
    Configure les commandes du bot au démarrage
    - Commandes publiques pour tous les utilisateurs
    - Commandes admin uniquement pour l'admin (si son chat_id est disponible)
    """
    
    # Commandes pour tous les utilisateurs (menu standard)
    public_commands = [
        BotCommand("start", "Start the bot"),
    ]
    
    # Commandes admin complètes
    admin_commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("broadcast", "📢 Send message to all users"),
        BotCommand("sendto", "📩 Send message to specific user"),
        BotCommand("sendto_gif", "🎬 Send GIF message to user"),
        BotCommand("listusers", "👥 List all users"),
        BotCommand("userinfo", "ℹ️ Get user information"),
        BotCommand("leaderboard", "🏆 View leaderboard"),
        BotCommand("profile", "👤 View profile"),
    ]
    
    # Définir les commandes publiques pour tout le monde
    await application.bot.set_my_commands(public_commands)
    logger.info("Public bot commands configured")
    
    # Essayer de configurer le menu admin
    try:
        # Récupérer le chat_id de l'admin depuis Firebase
        admin_doc = db.collection('users').document(ADMIN_USERNAME).get()
        
        if admin_doc.exists:
            admin_data = admin_doc.to_dict()
            admin_chat_id = admin_data.get('chat_id')
            
            if admin_chat_id:
                # Définir les commandes admin spécifiques pour le chat de l'admin
                await application.bot.set_my_commands(
                    commands=admin_commands,
                    scope=BotCommandScopeChat(chat_id=admin_chat_id)
                )
                logger.info(f"Admin commands configured for chat_id: {admin_chat_id}")
            else:
                logger.warning("Admin chat_id not found, admin menu not configured")
        else:
            logger.warning("Admin not found in database, admin menu not configured")
    
    except Exception as e:
        logger.error(f"Error configuring admin commands: {e}")


# ========================================
# COMMANDE POUR CONFIGURER LE MENU ADMIN MANUELLEMENT
# ========================================

async def setup_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Commande /setup_admin_menu - RÉSERVÉE À L'ADMIN
    Configure le menu admin avec toutes les commandes disponibles
    À utiliser si le menu admin n'a pas été configuré automatiquement
    """
    
    # Vérifier que l'utilisateur est bien l'admin
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    try:
        # Commandes admin complètes
        admin_commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("broadcast", "📢 Send message to all users"),
            BotCommand("sendto", "📩 Send message to specific user"),
            BotCommand("sendto_gif", "🎬 Send GIF message to user"),
            BotCommand("listusers", "👥 List all users"),
            BotCommand("userinfo", "ℹ️ Get user information"),
            BotCommand("leaderboard", "🏆 View leaderboard"),
            BotCommand("profile", "👤 View profile"),
        ]
        
        # Configurer les commandes pour ce chat spécifique
        admin_chat_id = update.effective_chat.id
        await context.bot.set_my_commands(
            commands=admin_commands,
            scope=BotCommandScopeChat(chat_id=admin_chat_id)
        )
        
        await update.message.reply_text(
            "✅ Admin menu configured successfully!\n\n"
            "You should now see all admin commands in your menu (/ button).\n\n"
            "Available commands:\n"
            "• /broadcast - Send to all users\n"
            "• /sendto - Send to specific user\n"
            "• /sendto_gif - Send GIF to user\n"
            "• /listusers - List all users\n"
            "• /userinfo - Get user info\n"
            "• /leaderboard - View leaderboard\n"
            "• /profile - View profile"
        )
        
        logger.info(f"Admin menu configured for {update.effective_user.username}")
        
    except Exception as e:
        logger.error(f"Error setting up admin menu: {e}")
        await update.message.reply_text(f"❌ Error configuring admin menu: {str(e)}")


# ========================================
# FONCTION PRINCIPALE
# ========================================

def main():
    """
    Point d'entrée principal du bot
    - Initialise l'application
    - Enregistre tous les handlers (commandes, callbacks, paiements)
    - Lance le polling pour écouter les messages
    """
    # Créer l'application avec le token et la fonction post_init
    application = ApplicationBuilder().token(API_TOKEN).post_init(post_init).build()

    # ========================================
    # HANDLERS DE COMMANDES PUBLIQUES
    # ========================================
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('leaderboard', leaderboard))
    application.add_handler(CommandHandler('profile', profile))
    
    # ========================================
    # HANDLERS DE COMMANDES ADMIN
    # ========================================
    application.add_handler(CommandHandler('broadcast', broadcast))
    application.add_handler(CommandHandler('sendto', sendto))
    application.add_handler(CommandHandler('sendto_gif', sendto_gif))
    application.add_handler(CommandHandler('listusers', listusers))
    application.add_handler(CommandHandler('userinfo', userinfo))
     application.add_handler(CommandHandler('setup_admin_menu', setup_admin_menu)
    
    # ========================================
    # HANDLER POUR LES BOUTONS INLINE
    # ========================================
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # ========================================
    # HANDLERS POUR LES PAIEMENTS TELEGRAM STARS
    # ========================================
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    # Démarrer le bot en mode polling (écoute continue des messages)
    logger.info("Bot started and listening for updates...")
    application.run_polling()


# ========================================
# POINT D'ENTRÉE
# ========================================

if __name__ == '__main__':
    main()