#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from browser_automation import create_user, assign_balance

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define conversation states
AWAITING_USERNAME, AWAITING_BALANCE = range(2)

# File to store user contexts
CONTEXT_FILE = 'user_contexts.json'

# Load user contexts from file or initialize empty dict
def load_user_contexts():
    try:
        if os.path.exists(CONTEXT_FILE):
            with open(CONTEXT_FILE, 'r') as f:
                # Convert string keys back to integers
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
        return {}
    except Exception as e:
        logger.error(f"Error loading user contexts: {e}")
        return {}

# Save user contexts to file
def save_user_contexts(contexts):
    try:
        # Convert keys to strings for JSON serialization
        serializable_contexts = {str(k): v for k, v in contexts.items()}
        with open(CONTEXT_FILE, 'w') as f:
            json.dump(serializable_contexts, f)
    except Exception as e:
        logger.error(f"Error saving user contexts: {e}")

# Store user context
user_contexts = load_user_contexts()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "Welcome to the Balance Loader Bot! 👋\n\n"
        "This bot automates user creation and balance loading on the platform.\n\n"
            "**How to use:**\n"
            "1. Send a username to create a new user\n"
            "   Example: `juanperez98`\n\n"
            "2. Reply to the bot's confirmation message with a load command\n"
            "   Example: `load 2000 pesos`\n\n"
            "Use /help for more information.",
            parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "🆘 **Help - Balance Loader Bot**\n\n"
            "**User Creation:**\n"
            "Send any message with a username to create a new user.\n"
            "The bot will use the static password: `cocos2025`\n\n"
            "**Balance Loading:**\n"
            "Reply to the bot's user creation confirmation with:\n"
            "`load [amount] pesos`\n\n"
            "**Examples:**\n"
            "• `juanperez98` (creates user)\n"
            "• `load 2000 pesos` (reply to confirmation)\n"
            "• `load 500` (reply to confirmation)\n\n"
            "**Notes:**\n"
            "• Balance loading only works when replying to the bot's user creation message\n"
            "• All new users get the password: cocos2025\n"
            "• Context never expires",
            parse_mode='Markdown'
    )

async def create_new_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user creation requests."""
    username = update.message.text.strip()
    
    # Check if the message is a valid username (no spaces, etc.)
    if ' ' in username or len(username) < 3:
        await update.message.reply_text(
            '❌ Invalid username. Please send a valid username without spaces.'
        )
        return
    
    # Fixed password as per requirements
    password = "cocos2025"
    
    # Send processing message
    processing_message = await update.message.reply_text(
        f"⏳ Creating user `{username}`... Please wait.",
        parse_mode='Markdown'
    )
    
    try:
        # Call the browser automation function to create the user
        success = await create_user(username, password)
        
        # Try to delete the processing message
        try:
            await processing_message.delete()
        except Exception as e:
            logger.warning(f"Could not delete processing message: {e}")
        
        if success:
            # Store the username in the context for future reference
            message = await update.message.reply_text(
                f"✅ **User created successfully!**\n\n"
                f"👤 Username: `{username}`\n"
                f"🔑 Password: `{password}`\n\n"
                f"💰 To load balance, reply to this message with:\n"
                f"`load [amount] pesos`",
                parse_mode='Markdown'
            )
            
            # Store the message ID and username for future reference
            user_contexts[message.message_id] = username
            
            # Save updated contexts to file
            save_user_contexts(user_contexts)
            
        else:
            await update.message.reply_text(
                "❌ Failed to create user. Please try again later."
            )
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        
        # Try to delete the processing message even if an error occurred
        try:
            await processing_message.delete()
        except Exception as delete_error:
            logger.warning(f"Could not delete processing message: {delete_error}")
            
        await update.message.reply_text(
            "❌ An error occurred while creating the user. Please try again later."
        )

async def load_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle balance loading requests."""
    # Check if this is a reply to a previous message
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ Please reply to a user creation message to load balance."
        )
        return
    
    # Get the message ID of the replied message
    replied_message_id = update.message.reply_to_message.message_id
    
    # Check if we have context for this message ID
    if replied_message_id not in user_contexts:
        await update.message.reply_text(
            "❌ Please reply to a valid user creation message."
        )
        return
    
    # Get the username from the context
    username = user_contexts[replied_message_id]
    
    # Parse the balance amount from the message
    message_text = update.message.text.lower()
    
    # Check if the message follows the expected format
    if not message_text.startswith("load ") or "pesos" not in message_text:
        await update.message.reply_text(
            "❌ Invalid format. Please use 'load X pesos'."
        )
        return
    
    try:
        # Extract the amount from the message
        amount_str = message_text.replace("load ", "").replace(" pesos", "")
        amount = int(amount_str)
        
        # Send processing message
        processing_message = await update.message.reply_text(
            f"⏳ Loading {amount} pesos to user `{username}`... Please wait.",
            parse_mode='Markdown'
        )
        
        try:
            # Call the browser automation function to assign balance
            success = await assign_balance(username, amount)
            
            # Try to delete the processing message
            try:
                await processing_message.delete()
            except Exception as e:
                logger.warning(f"Could not delete processing message: {e}")
            
            if success:
                await update.message.reply_text(
                    f"✅ **Balance loaded successfully!**\n\n"
                    f"👤 User: `{username}`\n"
                    f"💰 Amount: `{amount} pesos`",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ Failed to load balance. Please try again later."
                )
        except Exception as e:
            logger.error(f"Error loading balance: {e}")
            
            # Try to delete the processing message even if an error occurred
            try:
                await processing_message.delete()
            except Exception as delete_error:
                logger.warning(f"Could not delete processing message: {delete_error}")
                
            await update.message.reply_text(
                "❌ An error occurred while loading balance. Please try again later."
            )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount. Please provide a valid number."
        )

def main() -> None:
    """Start the bot."""
    # Load user contexts from file
    global user_contexts
    user_contexts = load_user_contexts()
    
    # Create the Application
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.REPLY, load_balance))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.REPLY, create_new_user))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()