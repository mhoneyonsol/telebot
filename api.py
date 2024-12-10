# api.py

from flask import Flask, request, jsonify
import telegram
import os
import firebase_admin
from firebase_admin import credentials, firestore
import json
from dotenv import load_dotenv
from functools import wraps
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
API_TOKEN = os.getenv("API_TOKEN")  # Telegram Bot API Token
CHANNEL_USERNAME = "@pxlonton"      # Your Telegram channel username
API_KEY = os.getenv("API_KEY")      # Define a secure API key in your .env file

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

app = Flask(__name__)

# Simple API key authentication
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'x-api-key' not in request.headers:
            logger.warning("API key missing in request headers.")
            return jsonify({'error': 'API key missing'}), 401
        if request.headers['x-api-key'] != API_KEY:
            logger.warning("Invalid API key provided.")
            return jsonify({'error': 'Invalid API key'}), 403
        return f(*args, **kwargs)
    return decorated

@app.route('/api/telegram/verify', methods=['POST'])
@require_api_key
def verify_telegram_membership():
    data = request.get_json()
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
        member = bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=int(user_id))
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
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000)
