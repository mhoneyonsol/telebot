import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler

API_TOKEN = '7413088498:AAHIHrC2jO4DGy0FFa7pX9tNJ8KS-ED89II'

# Setup logging to debug issues
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
aimport logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Poll
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, PollHandler

API_TOKEN = '7413088498:AAHIHrC2jO4DGy0FFa7pX9tNJ8KS-ED89II'

# Setup logging to debug issues
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Handler for the /start command
def start(update, context):
    welcome_message = """
🎉 *Welcome to PixelWar!* 🎉
You're embarking on an exciting adventure on the TON blockchain! 🚀

💰 *Start buying and selling pixels* and join pixel art battles to win TON.

👇 *Select an option below to get started and begin winning*:
    """

    keyboard = [
        [InlineKeyboardButton("🎨 Pixel MAP", url='https://t.me/pxltonbot/buypixels')],
        [InlineKeyboardButton("⚔️ Battle Pixel Art", url='https://t.me/pxltonbot/artbattle')],
        [InlineKeyboardButton("👤 Profil", callback_data='profile')],
        [InlineKeyboardButton("🎁 Rewards", callback_data='rewards')],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data='leaderboard')],
        [InlineKeyboardButton("🗳️ Start Poll", callback_data='start_poll')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

# Function to start a poll
def start_poll(update, context):
    question = "What's your favorite pixel color?"
    options = ["Red", "Blue", "Green", "Yellow"]
    update.message.reply_poll(question, options)

# Handler for poll answers
def handle_poll_answer(update, context):
    poll_answer = update.poll_answer
    user_id = update.effective_user.id
    chosen_option = poll_answer.option_ids
    context.bot.send_message(chat_id=user_id, text=f"You voted for option {chosen_option}")

# Handler for callback queries
def button(update, context):
    query = update.callback_query
    data = query.data

    if data == 'start_poll':
        start_poll(update, context)

# Main function to set up the bot
def main():
    # Create an Updater object with the bot token
    updater = Updater(token=API_TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add handlers for the /start command and button presses
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CallbackQueryHandler(button))
    
    # Add handlers for poll features
    dispatcher.add_handler(PollHandler(handle_poll_answer))

    # Start polling for updates from Telegram
    updater.start_polling()

    # Block until you press Ctrl+C or the process is terminated
    updater.idle()

if __name__ == '__main__':
    main()

# Handler for the /start command
def start(update, context):
    welcome_message = """
🎉 *Welcome to PixelWar!* 🎉
You're embarking on an exciting adventure on the TON blockchain! 🚀

💰 *Start buying and selling pixels* and join pixel art battles to win TON.

👇 *Select an option below to get started and begin winning*:
    """



    
    keyboard = [
        [InlineKeyboardButton("🎨 Pixel MAP", url='https://t.me/pxltonbot/buypixels')],
        [InlineKeyboardButton("⚔️ Battle Pixel Art", url='https://t.me/pxltonbot/artbattle')],
        [InlineKeyboardButton("👤 Profil", callback_data='profile')],
        [InlineKeyboardButton("🎁 Rewards", callback_data='rewards')],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data='leaderboard')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

# Main function to set up the bot
def main():
    # Create an Updater object with the bot token
    updater = Updater(token=API_TOKEN, use_context=True)

    # Add a handler for the /start command
    updater.dispatcher.add_handler(CommandHandler('start', start))

    # Start polling for updates from Telegram
    updater.start_polling()

    # Block until you press Ctrl+C or the process is terminated
    updater.idle()

if __name__ == '__main__':
    main()
