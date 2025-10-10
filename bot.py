"""
BOT TELEGRAM TOKEARN
Bot pour gérer les interactions Telegram avec l'application Tokearn
Fonctionnalités: Profile, Leaderboard, Referral system, Broadcast
"""

from datetime import datetime
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot, Update, BotCommand
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
    Ces commandes apparaissent dans le menu Telegram (bouton "/" en bas à gauche)
    """
    commands = [
        BotCommand("start", "Start the bot"),
        # On peut ajouter d'autres commandes ici si nécessaire
        # BotCommand("leaderboard", "View leaderboard"),
        # BotCommand("profile", "View your profile"),
    ]
    
    await application.bot.set_my_commands(commands)
    logger.info("Bot commands configured successfully")


# ========================================
# FONCTION PRINCIPALE
# ========================================

def main():
    """
    Point d'entrée principal du bot
    - Initialise l'application
    - Enregistre tous les handlers
    - Lance le polling
    """
    # Créer l'application avec le token et la fonction post_init
    application = ApplicationBuilder().token(API_TOKEN).post_init(post_init).build()

    # Enregistrer les handlers de commandes
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('broadcast', broadcast))
    application.add_handler(CommandHandler('leaderboard', leaderboard))
    application.add_handler(CommandHandler('profile', profile))
    
    # Enregistrer le handler pour les boutons inline
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Enregistrer les handlers pour les paiements Telegram Stars
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