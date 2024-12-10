from quart import Quart, request, jsonify
from quart_cors import cors
import telegram
import os
import firebase_admin
from firebase_admin import credentials, firestore
import json
from dotenv import load_dotenv
import logging


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
try:
    cred = credentials.Certificate(json.loads(json.dumps(firebase_config)))
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("Firebase initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {e}")
    exit(1)

app = Quart(__name__)




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

if __name__ == '__main__':
    # Run the Quart app with the dynamically assigned port from Heroku
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
