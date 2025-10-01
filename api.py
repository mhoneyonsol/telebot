from quart import Quart, request, jsonify
from quart_cors import cors
import telegram
import os
import firebase_admin
from firebase_admin import credentials, firestore
import json
from dotenv import load_dotenv
import logging
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

@app.route('/api/notify-referral', methods=['POST'])
async def notify_referral():
    """Endpoint to send referral notification"""
    try:
        data = await request.get_json()
        
        if not data or 'referrer' not in data or 'new_user' not in data:
            return jsonify({'error': 'Missing parameters'}), 400
        
        referrer = data['referrer']
        new_user = data['new_user']
        
        logger.info(f"Sending referral notification: {new_user} joined via {referrer}'s link")
        
        # Get referrer's chat_id from Firebase
        referrer_doc = db.collection('users').document(referrer).get()
        
        if not referrer_doc.exists:
            logger.warning(f"Referrer {referrer} not found in Firebase")
            return jsonify({'error': 'Referrer not found'}), 404
        
        referrer_data = referrer_doc.to_dict()
        chat_id = referrer_data.get('chat_id')
        
        if not chat_id:
            logger.warning(f"No chat_id for referrer {referrer}")
            return jsonify({'error': 'No chat_id'}), 404
        
        # Create notification message
        message = f"""
🎉 *Congratulations!*

*{new_user}* just joined our community using your referral link!

💰 You earned *1,000 NES* tokens!

Keep sharing to unlock bigger rewards! 🚀
"""
        
        # Create keyboard
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎮 Open App", url="https://t.me/nestortonbot/hello")],
            [InlineKeyboardButton("📢 Share Again", url=f"https://t.me/share/url?url=https://t.me/nestortonbot?start=ref_{referrer_data.get('referral_code', '')}")]
        ])
        
        # Send notification
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        logger.info(f"Telegram notification sent to {referrer} (chat_id: {chat_id})")
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error in notify-referral endpoint: {e}")
        return jsonify({'error': str(e)}), 500
        

if __name__ == '__main__':
    # Run the Quart app with the dynamically assigned port from Heroku
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
