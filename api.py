from quart import Quart, request, jsonify
from quart_cors import cors
import telegram
import os
import firebase_admin
from firebase_admin import credentials, firestore
import json
from dotenv import load_dotenv
import logging
import random
from decimal import Decimal
from bot import send_referral_notification
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# Load environment variables from .env file
load_dotenv()

# Initialize logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment Variables
API_TOKEN = os.getenv("API_TOKEN")  # Telegram Bot API token
CHANNEL_USERNAME = "@pxlonton"  # Your Telegram channel username
API_KEY = os.getenv("API_KEY")  # Secure API key for the Flask API


# Initialize Telegram Bot
bot = telegram.Bot(token=API_TOKEN)

# Initialize Firebase
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

# Initialize Firebase Admin SDK
# Initialize Firebase Admin SDK
try:
    # Utilise une app Firebase avec un nom unique pour api.py
    try:
        app_firebase = firebase_admin.get_app('api_app')
    except ValueError:
        # L'app n'existe pas encore, on la crée
        cred = credentials.Certificate(json.loads(json.dumps(firebase_config)))
        app_firebase = firebase_admin.initialize_app(cred, name='api_app')
    
    db = firestore.client(app=app_firebase)
    logger.info("Firebase initialized successfully for API.")
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {e}")
    exit(1)

app = Quart(__name__)

ALLOWED_ORIGIN = "https://tokearn-a67df5f503a2.herokuapp.com"

app = cors(app, allow_origin=[
    "https://tokearn-a67df5f503a2.herokuapp.com",
    "https://t.me",
    "https://telegram.org"
], allow_methods=['GET', 'POST', 'OPTIONS'], 
allow_headers=['Content-Type', 'Authorization', 'x-api-key'])

@app.route('/api/notify-referral', methods=['OPTIONS'])
async def notify_referral_options():
    """Handle preflight requests"""
    return '', 204

# Simple API key authentication
def require_api_key(f):
    async def decorated(*args, **kwargs):
        if 'x-api-key' not in request.headers:
            logger.warning("API key missing in request headers.")
            return jsonify({'error': 'API key missing'}), 401
        if request.headers['x-api-key'] != API_KEY:
            logger.warning("Invalid API key provided.")
            return jsonify({'error': 'Invalid API key'}), 403
        return await f(*args, **kwargs)
    return decorated

@app.route('/proxy/verify-membership', methods=['POST'])
async def proxy_verify_membership():
    """
    This endpoint acts as a proxy for verifying Telegram membership.
    It securely calls the main `/api/telegram/verify` endpoint with the API_KEY.
    """
    data = await request.get_json()
    if not data or 'username' not in data:
        logger.error("Missing 'username' in request body.")
        return jsonify({'error': 'Missing username'}), 400

    username = data['username']
    logger.info(f"Proxy received request for username: {username}")

    try:
        # Call the internal verification endpoint with the API_KEY
        url = "https://guarded-forest-98367-6965ee2800e6.herokuapp.com/api/telegram/verify"
        headers = {"Content-Type": "application/json", "x-api-key": API_KEY}
        payload = {"username": username}

        # Use an asynchronous HTTP client to make the call
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                result = await response.json()
                return jsonify(result), response.status
    except Exception as e:
        logger.error(f"Error in proxy verification: {e}")
        return jsonify({'error': str(e)}), 500


# Configuration des collectibles
NFT_COLLECTIBLES_CONFIG = {
    "1": {
        "bet": 1.0,
        "gifts": [
            {"id": "gift1_1", "name": "Green Crystal", "rarity": "common", "chance": 20},
            {"id": "gift1_2", "name": "Blue Gem", "rarity": "common", "chance": 18},
            {"id": "gift1_3", "name": "Purple Stone", "rarity": "uncommon", "chance": 15},
            {"id": "gift1_4", "name": "Golden Nugget", "rarity": "uncommon", "chance": 12},
            {"id": "gift1_5", "name": "Ruby Fragment", "rarity": "rare", "chance": 8},
            {"id": "gift1_6", "name": "Diamond Piece", "rarity": "rare", "chance": 5},
            {"id": "gift1_7", "name": "Legendary Ore", "rarity": "epic", "chance": 3},
            {"id": "gift1_8", "name": "Mythic Crystal", "rarity": "legendary", "chance": 1}
        ],
        "ton_prizes": [
            {"amount": 0.2, "chance": 10},
            {"amount": 0.5, "chance": 5}
        ],
        "loss_chance": 3
    },
    "3": {
        "bet": 3.0,
        "gifts": [
            {"id": "gift3_1", "name": "Silver Crystal", "rarity": "common", "chance": 18},
            {"id": "gift3_2", "name": "Aqua Gem", "rarity": "common", "chance": 16},
            {"id": "gift3_3", "name": "Emerald Stone", "rarity": "uncommon", "chance": 14},
            {"id": "gift3_4", "name": "Gold Nugget", "rarity": "uncommon", "chance": 12},
            {"id": "gift3_5", "name": "Ruby Crystal", "rarity": "rare", "chance": 10},
            {"id": "gift3_6", "name": "Big Diamond", "rarity": "rare", "chance": 7},
            {"id": "gift3_7", "name": "Mythic Ore", "rarity": "epic", "chance": 4},
            {"id": "gift3_8", "name": "Ancient Relic", "rarity": "legendary", "chance": 2}
        ],
        "ton_prizes": [
            {"amount": 0.5, "chance": 8},
            {"amount": 2.5, "chance": 4}
        ],
        "loss_chance": 5
    },
    "6": {
        "bet": 6.0,
        "gifts": [
            {"id": "gift6_1", "name": "Platinum Crystal", "rarity": "common", "chance": 16},
            {"id": "gift6_2", "name": "Sapphire Gem", "rarity": "common", "chance": 14},
            {"id": "gift6_3", "name": "Jade Stone", "rarity": "uncommon", "chance": 12},
            {"id": "gift6_4", "name": "Pure Gold", "rarity": "uncommon", "chance": 10},
            {"id": "gift6_5", "name": "Ruby Cluster", "rarity": "rare", "chance": 8},
            {"id": "gift6_6", "name": "Mega Diamond", "rarity": "rare", "chance": 6},
            {"id": "gift6_7", "name": "Divine Artifact", "rarity": "epic", "chance": 3},
            {"id": "gift6_8", "name": "Celestial Gem", "rarity": "legendary", "chance": 1}
        ],
        "ton_prizes": [
            {"amount": 0.8, "chance": 12},
            {"amount": 5.5, "chance": 3}
        ],
        "loss_chance": 15
    },
    "10": {
        "bet": 10.0,
        "gifts": [
            {"id": "gift10_1", "name": "Titanium Crystal", "rarity": "common", "chance": 14},
            {"id": "gift10_2", "name": "Cosmic Gem", "rarity": "common", "chance": 12},
            {"id": "gift10_3", "name": "Obsidian Stone", "rarity": "uncommon", "chance": 10},
            {"id": "gift10_4", "name": "Royal Gold", "rarity": "uncommon", "chance": 8},
            {"id": "gift10_5", "name": "Ruby Crown", "rarity": "rare", "chance": 6},
            {"id": "gift10_6", "name": "Ultimate Diamond", "rarity": "rare", "chance": 4},
            {"id": "gift10_7", "name": "Supreme Artifact", "rarity": "epic", "chance": 2},
            {"id": "gift10_8", "name": "Omega Crystal", "rarity": "legendary", "chance": 0.5}
        ],
        "ton_prizes": [
            {"amount": 1.0, "chance": 22},
            {"amount": 9.8, "chance": 5}
        ],
        "loss_chance": 16.5
    }
}


def nft_calculate_prize(bet_level: str):
    """Calcule le gain aléatoire"""
    config = NFT_COLLECTIBLES_CONFIG[bet_level]
    
    outcomes = []
    
    # NFTs
    for gift in config["gifts"]:
        outcomes.extend([("collectible", gift)] * int(gift["chance"] * 10))
    
    # TON
    for prize in config["ton_prizes"]:
        outcomes.extend([("ton", prize)] * int(prize["chance"] * 10))
    
    # Pertes
    outcomes.extend([("loss", None)] * int(config["loss_chance"] * 10))
    
    result_type, result_item = random.choice(outcomes)
    
    if result_type == "collectible":
        return {
            "type": "collectible",
            "collectible": result_item,
            "rarity": result_item["rarity"]
        }
    elif result_type == "ton":
        return {
            "type": "ton",
            "amount": result_item["amount"]
        }
    else:
        return {"type": "loss"}


@app.route('/api/chance/deposit', methods=['POST', 'OPTIONS'])
async def nft_deposit():
    """Déposer des TON dans le wallet interne"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = await request.get_json()
        
        username = data.get('username')
        wallet_address = data.get('wallet')
        amount = float(data.get('amount'))
        tx_hash = data.get('txHash')
        
        if not all([username, wallet_address, amount, tx_hash]):
            return jsonify({'error': 'Missing fields'}), 400
        
        logger.info(f"💰 Deposit: {username} - {amount} TON")
        
        user_wallet_ref = db.collection('game_wallets').document(username)
        user_wallet = user_wallet_ref.get()
        
        if user_wallet.exists:
            current_balance = user_wallet.to_dict().get('balance', 0)
            new_balance = current_balance + amount
            user_wallet_ref.update({
                'balance': new_balance,
                'last_deposit': firestore.SERVER_TIMESTAMP,
                'total_deposited': firestore.FieldValue.increment(amount)
            })
        else:
            new_balance = amount
            user_wallet_ref.set({
                'username': username,
                'wallet_address': wallet_address,
                'balance': amount,
                'collectibles': [],
                'total_deposited': amount,
                'total_withdrawn': 0,
                'created_at': firestore.SERVER_TIMESTAMP
            })
        
        db.collection('deposits').add({
            'username': username,
            'wallet': wallet_address,
            'amount': amount,
            'tx_hash': tx_hash,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        logger.info(f"✅ Deposit successful: {username}")
        
        return jsonify({
            'success': True,
            'new_balance': new_balance
        }), 200
        
    except Exception as e:
        logger.error(f"Deposit error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chance/balance/<username>', methods=['GET'])
async def nft_get_balance(username):
    """Récupérer le solde"""
    try:
        user_wallet_ref = db.collection('game_wallets').document(username)
        user_wallet = user_wallet_ref.get()
        
        if not user_wallet.exists:
            return jsonify({
                'balance': 0,
                'collectibles': []
            }), 200
        
        data = user_wallet.to_dict()
        
        return jsonify({
            'balance': data.get('balance', 0),
            'collectibles': data.get('collectibles', [])
        }), 200
        
    except Exception as e:
        logger.error(f"Balance error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chance/play', methods=['POST', 'OPTIONS'])
async def nft_play_game():
    """Jouer au jeu"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = await request.get_json()
        
        username = data.get('username')
        bet_level = str(data.get('betLevel'))
        
        if not username or bet_level not in NFT_COLLECTIBLES_CONFIG:
            return jsonify({'error': 'Invalid request'}), 400
        
        bet_amount = NFT_COLLECTIBLES_CONFIG[bet_level]["bet"]
        
        logger.info(f"🎰 {username} playing {bet_level} TON")
        
        user_wallet_ref = db.collection('game_wallets').document(username)
        user_wallet = user_wallet_ref.get()
        
        if not user_wallet.exists:
            return jsonify({'error': 'No wallet found'}), 400
        
        wallet_data = user_wallet.to_dict()
        current_balance = wallet_data.get('balance', 0)
        
        if current_balance < bet_amount:
            return jsonify({'error': 'Insufficient balance'}), 400
        
        # Calculer le gain
        prize = nft_calculate_prize(bet_level)
        
        new_balance = current_balance - bet_amount
        
        if prize["type"] == "collectible":
            collectibles = wallet_data.get('collectibles', [])
            collectibles.append({
                'id': prize["collectible"]["id"],
                'name': prize["collectible"]["name"],
                'rarity': prize["rarity"],
                'won_at': firestore.SERVER_TIMESTAMP,
                'bet_level': bet_level
            })
            
            user_wallet_ref.update({
                'balance': new_balance,
                'collectibles': collectibles
            })
            
            result = {
                'success': True,
                'type': 'collectible',
                'collectible': prize["collectible"],
                'rarity': prize["rarity"]
            }
            
        elif prize["type"] == "ton":
            new_balance += prize["amount"]
            
            user_wallet_ref.update({
                'balance': new_balance
            })
            
            result = {
                'success': True,
                'type': 'ton',
                'amount': prize["amount"]
            }
            
        else:
            user_wallet_ref.update({
                'balance': new_balance
            })
            
            result = {
                'success': True,
                'type': 'loss'
            }
        
        # Sauvegarder historique
        db.collection('game_history').add({
            'username': username,
            'bet_level': bet_level,
            'bet_amount': bet_amount,
            'result': result,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        logger.info(f"✅ Game result: {result['type']}")
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Game error: {e}")
        return jsonify({'error': str(e)}), 500        

@app.route('/api/telegram/verify', methods=['POST'])
@require_api_key
async def verify_telegram_membership():
    """
    Main endpoint to verify Telegram membership.
    This endpoint should not be directly accessible by the client-side code.
    """
    data = await request.get_json()
    if not data or 'username' not in data:
        logger.error("Missing 'username' in request body.")
        return jsonify({'error': 'Missing username'}), 400

    username = data['username']
    logger.info(f"Received verification request for username: {username}")

    # Fetch user's Telegram user_id from Firestore using username
    user_doc_ref = db.collection('users').document(username)
    user_doc = user_doc_ref.get()

    if not user_doc.exists:
        logger.error(f"User '{username}' not found in Firestore.")
        return jsonify({'error': 'User not found'}), 404

    user_data = user_doc.to_dict()
    user_id = user_data.get('user_id')

    if not user_id:
        logger.error(f"'user_id' not found for user '{username}'.")
        return jsonify({'error': 'User ID not found'}), 400

    try:
        # Use await for asynchronous call
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=int(user_id))
        status = member.status
        is_member = status in ['member', 'administrator', 'creator']
        logger.info(f"User '{username}' membership status: {status}")
        return jsonify({'isMember': is_member})
    except telegram.error.BadRequest as e:
        logger.error(f"BadRequest Error: {e}")
        return jsonify({'error': f'Bad Request: {str(e)}'}), 400
    except telegram.error.TelegramError as e:
        logger.error(f"Telegram API Error: {e}")
        return jsonify({'error': f'Telegram API Error: {str(e)}'}), 500


@app.route('/api/public/create-stars-invoice', methods=['POST'])
async def create_stars_invoice_public():
    """
    Endpoint public pour créer des factures Stars (sans API key)
    Sécurisé par validation des données Telegram
    """
    try:
        data = await request.get_json()
        if not data:
            return jsonify({'error': 'Missing request data'}), 400

        amount = data.get('amount')
        description = data.get('description', 'Premium purchase')
        user_id = data.get('userId')
        
        # Validation basique
        if not amount or not user_id or amount <= 0 or amount > 1000:
            return jsonify({'error': 'Invalid amount or userId'}), 400

        # Vérifier que le user_id existe dans votre base
        users_ref = db.collection('users')
        query = users_ref.where('user_id', '==', int(user_id)).limit(1)
        docs = list(query.stream())
        
        if not docs:
            return jsonify({'error': 'User not found'}), 404

        logger.info(f"Creating Stars invoice: {amount} stars for user {user_id}")

        # Créer la facture avec l'API Telegram Bot
        invoice = await bot.create_invoice_link(
            title="Premium Purchase",
            description=description,
            payload=f"stars_payment_{user_id}_{amount}",
            provider_token="",  # Vide pour Telegram Stars
            currency="XTR",  # Telegram Stars currency
            prices=[telegram.LabeledPrice(label=description, amount=amount)]
        )

        logger.info(f"Invoice created successfully")
        
        return jsonify({
            'success': True,
            'invoice_url': invoice
        })

    except Exception as e:
        logger.error(f"Error creating Stars invoice: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/notify-referral', methods=['POST', 'OPTIONS'])
async def notify_referral():
    """Endpoint to send referral notification"""
    
    # Handle preflight CORS
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = await request.get_json()
        
        if not data or 'referrer' not in data or 'new_user' not in data:
            logger.error("Missing parameters in notify-referral request")
            return jsonify({'error': 'Missing parameters'}), 400
        
        referrer = data['referrer']
        new_user = data['new_user']
        
        logger.info(f"Processing referral notification: {new_user} -> {referrer}")
        
        # Get referrer's chat_id from Firebase
        try:
            referrer_doc = db.collection('users').document(referrer).get()
            
            if not referrer_doc.exists:
                logger.warning(f"Referrer {referrer} not found in Firebase")
                return jsonify({'error': 'Referrer not found'}), 404
            
            referrer_data = referrer_doc.to_dict()
            chat_id = referrer_data.get('chat_id')
            friends_count = referrer_data.get('friends_invited', 0)
            
            if not chat_id:
                logger.warning(f"No chat_id for referrer {referrer}")
                return jsonify({'error': 'No chat_id'}), 404
            
            logger.info(f"Found chat_id {chat_id} for referrer {referrer}, friends: {friends_count}")
            
        except Exception as e:
            logger.error(f"Firebase error: {e}")
            return jsonify({'error': 'Database error'}), 500
        
        # Calculate reward based on milestone
        reward = 1000  # Base reward
        milestone_bonus = 0
        milestone_name = ""

        if friends_count == 5:
            milestone_bonus = 5000
            milestone_name = "🏅 Recruteur Badge unlocked!"
        elif friends_count == 10:
            milestone_bonus = 4500
            milestone_name = "🎖️ Ambassadeur Badge unlocked!"
        elif friends_count == 25:
            milestone_bonus = 39500
            milestone_name = "👑 Legend Badge unlocked!"
        elif friends_count == 50:
            milestone_bonus = 100000
            milestone_name = "💎 Elite Badge unlocked!"

        total_reward = reward + milestone_bonus

        # Create notification message
        if milestone_bonus > 0:
            message = f"""
🎉 *Congratulations!*

*{new_user}* just joined our community using your referral link!

💰 You earned *{total_reward:,} NES* tokens!
   • Base reward: {reward:,} NES
   • Milestone bonus: {milestone_bonus:,} NES

{milestone_name}

Total friends invited: *{friends_count}*

Keep sharing to unlock bigger rewards! 🚀
"""
        else:
            message = f"""
🎉 *Congratulations!*

*{new_user}* just joined our community using your referral link!

💰 You earned *{reward:,} NES* tokens!

Total friends invited: *{friends_count}*

Keep sharing to unlock bigger rewards! 🚀
"""
        
        try:
            # Create keyboard
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Open App", url="https://t.me/nestortonbot/hello")],
                [InlineKeyboardButton("📢 Share Again", 
                    url=f"https://t.me/share/url?url=https://t.me/nestortonbot?start=ref_{referrer_data.get('referral_code', '')}")]
            ])
            
            # Send notification
            logger.info(f"Attempting to send Telegram message to chat_id {chat_id}")
            
            await bot.send_message(
                chat_id=int(chat_id),
                text=message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
            logger.info(f"✅ Telegram notification sent successfully to {referrer}")
            return jsonify({'success': True}), 200
            
        except Exception as e:
            logger.error(f"Telegram API error: {e}")
            return jsonify({'error': f'Telegram error: {str(e)}'}), 500
            
    except Exception as e:
        logger.error(f"Unexpected error in notify-referral: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
        


@app.route('/api/notify-level-bonus', methods=['POST', 'OPTIONS'])
async def notify_level_bonus():
    """Notify referrer when their friend levels up"""
    
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = await request.get_json()
        
        if not data or 'referrer' not in data or 'friend' not in data:
            return jsonify({'error': 'Missing parameters'}), 400
        
        referrer = data['referrer']
        friend = data['friend']
        level = data.get('level', 0)
        bonus = data.get('bonus', 0)
        
        logger.info(f"Level bonus notification: {friend} reached level {level}")
        
        referrer_doc = db.collection('users').document(referrer).get()
        
        if not referrer_doc.exists:
            return jsonify({'error': 'Referrer not found'}), 404
        
        referrer_data = referrer_doc.to_dict()
        chat_id = referrer_data.get('chat_id')
        
        if not chat_id:
            return jsonify({'error': 'No chat_id'}), 404
        
        message = f"""
🎉 *Level Up Bonus!*

Your friend *{friend}* just reached *Level {level}*!

💰 You earned *{bonus:,} NES* tokens!

Keep encouraging your friends to play! 🚀
"""
        
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Open App", url="https://t.me/nestortonbot/hello")],
            [InlineKeyboardButton("👥 View Referrals", url="https://t.me/nestortonbot/hello#referral")]
        ])
        
        await bot.send_message(
            chat_id=int(chat_id),
            text=message,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        logger.info(f"Level bonus notification sent to {referrer}")
        return jsonify({'success': True}), 200
        
    except Exception as e:
        logger.error(f"Error in notify-level-bonus: {e}")
        return jsonify({'error': str(e)}), 500



if __name__ == '__main__':
    # Run the Quart app with the dynamically assigned port from Heroku
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
