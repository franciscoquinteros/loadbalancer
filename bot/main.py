#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
import signal
import sys
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from browser_automation import create_user, assign_balance, cleanup_browser
from pathlib import Path

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

# File to store user settings
SETTINGS_FILE = 'user_settings.json'

# Load user settings from file or initialize empty dict
def load_user_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                # Convert string keys back to integers
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
        return {}
    except Exception as e:
        logger.error(f"Error loading user settings: {e}")
        return {}

# Save user settings to file
def save_user_settings(settings):
    try:
        # Convert keys to strings for JSON serialization
        serializable_settings = {str(k): v for k, v in settings.items()}
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(serializable_settings, f)
    except Exception as e:
        logger.error(f"Error saving user settings: {e}")

# Store user context
user_contexts = load_user_contexts()

# Store user settings
user_settings = load_user_settings()

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
            "**Commands:**\n"
            "• `/start` - Show welcome message\n"
            "• `/help` - Show this help\n"
            "• `/clear_context` - Clear saved browser session\n"
            "• `/reset_confirmations` - Re-enable confirmation messages\n\n"
            "**Notes:**\n"
            "• Balance loading only works when replying to the bot's user creation message\n"
            "• All new users get the password: cocos2025\n"
            "• Context never expires\n"
            "• Browser session is saved to avoid re-login\n"
            "• You can disable confirmation messages permanently",
            parse_mode='Markdown'
    )

async def clear_browser_context(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear the saved browser context."""
    try:
        # Clear the browser context
        await cleanup_browser()
        
        # Remove the saved context file
        context_file = Path("browser_context/state.json")
        if context_file.exists():
            context_file.unlink()
            
        context_dir = Path("browser_context")
        if context_dir.exists() and not any(context_dir.iterdir()):
            context_dir.rmdir()
        
        await update.message.reply_text(
            "✅ Browser context cleared successfully. The bot will need to login again on the next operation."
        )
        
    except Exception as e:
        logger.error(f"Error clearing browser context: {e}")
        await update.message.reply_text(
            "❌ Error clearing browser context. Please try again later."
        )

async def create_new_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user creation requests."""
    username = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Check if the message is a valid username (no spaces, etc.)
    if ' ' in username or len(username) < 3:
        await update.message.reply_text(
            '❌ Invalid username. Please send a valid username without spaces.'
        )
        return
    
    # Check if user has disabled confirmations
    if user_settings.get(user_id, {}).get('skip_confirmation', False):
        # Skip confirmation and create user directly
        await process_user_creation(update, context, username)
        return
    
    # Show confirmation message with buttons
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_user:{username}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_user")
        ],
        [
            InlineKeyboardButton("🔕 Don't ask again", callback_data=f"skip_confirm:{username}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🤔 **Create User Confirmation**\n\n"
        f"👤 Username: `{username}`\n"
        f"🔑 Password: `cocos2025`\n\n"
        f"Do you want to create this user?",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks"""
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()
    
    if query.data.startswith("confirm_user:"):
        # Extract username from callback data
        username = query.data.split("confirm_user:")[1]
        
        # Edit the message to show processing
        await query.edit_message_text(
            f"⏳ Creating user `{username}`... Please wait.",
            parse_mode='Markdown'
        )
        
        # Create the user
        await process_user_creation_from_callback(query, context, username)
        
    elif query.data == "cancel_user":
        # User cancelled
        await query.edit_message_text(
            "❌ User creation cancelled."
        )
        
    elif query.data.startswith("skip_confirm:"):
        # User wants to skip confirmations in the future
        username = query.data.split("skip_confirm:")[1]
        
        # Update user settings
        if user_id not in user_settings:
            user_settings[user_id] = {}
        user_settings[user_id]['skip_confirmation'] = True
        save_user_settings(user_settings)
        
        # Edit the message to show processing
        await query.edit_message_text(
            f"⏳ Creating user `{username}`... Please wait.\n\n"
            f"✅ Confirmation disabled for future operations.",
            parse_mode='Markdown'
        )
        
        # Create the user
        await process_user_creation_from_callback(query, context, username)

async def process_user_creation(update: Update, context: ContextTypes.DEFAULT_TYPE, username: str) -> None:
    """Process user creation (for direct calls)"""
    # Fixed password as per requirements
    password = "cocos2025"
    
    # Send processing message
    processing_message = await update.message.reply_text(
        f"⏳ Creating user `{username}`... Please wait.",
        parse_mode='Markdown'
    )
    
    try:
        # Call the browser automation function to create the user
        success, message = await create_user(username, password)
        
        # Try to delete the processing message
        try:
            await processing_message.delete()
        except Exception as e:
            logger.warning(f"Could not delete processing message: {e}")
        
        if success:
            # Store the username in the context for future reference
            reply_message = await update.message.reply_text(
                f"✅ **User created successfully!**\n\n"
                f"👤 Username: `{username}`\n"
                f"🔑 Password: `{password}`\n\n"
                f"💰 To load balance, reply to this message with:\n"
                f"`load [amount] pesos`",
                parse_mode='Markdown'
            )
            
            # Store the message ID and username for future reference
            user_contexts[reply_message.message_id] = username
            
            # Save updated contexts to file
            save_user_contexts(user_contexts)
            
        else:
            await update.message.reply_text(
                f"❌ **Failed to create user**\n\n"
                f"Please try again with different username.",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        
        # Try to delete the processing message even if an error occurred
        try:
            await processing_message.delete()
        except Exception as delete_error:
            logger.warning(f"Could not delete processing message: {delete_error}")
            
        await update.message.reply_text(
            f"❌ **An error occurred while creating the user**\n\n"
            f"Please try again with different username.",
            parse_mode='Markdown'
        )

async def process_user_creation_from_callback(query, context: ContextTypes.DEFAULT_TYPE, username: str) -> None:
    """Process user creation (for callback queries)"""
    # Fixed password as per requirements
    password = "cocos2025"
    
    try:
        # Call the browser automation function to create the user
        success, message = await create_user(username, password)
        
        if success:
            # Edit the message to show success
            reply_text = (
                f"✅ **User created successfully!**\n\n"
                f"👤 Username: `{username}`\n"
                f"🔑 Password: `{password}`\n\n"
                f"💰 To load balance, reply to this message with:\n"
                f"`load [amount] pesos`"
            )
            
            await query.edit_message_text(
                reply_text,
                parse_mode='Markdown'
            )
            
            # Store the message ID and username for future reference
            # Note: We use the edited message for context
            user_contexts[query.message.message_id] = username
            
            # Save updated contexts to file
            save_user_contexts(user_contexts)
            
        else:
            await query.edit_message_text(
                f"❌ **Failed to create user**\n\n"
                f"Please try again with different username.",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        
        await query.edit_message_text(
            f"❌ **An error occurred while creating the user**\n\n"
            f"Please try again with different username.",
            parse_mode='Markdown'
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
            success, message = await assign_balance(username, amount)
            
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
                    f"❌ **Failed to load balance**\n\n"
                    f"**Error:** {message}\n\n"
                    f"Please try again later.",
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Error loading balance: {e}")
            
            # Try to delete the processing message even if an error occurred
            try:
                await processing_message.delete()
            except Exception as delete_error:
                logger.warning(f"Could not delete processing message: {delete_error}")
                
            await update.message.reply_text(
                f"❌ **An error occurred while loading balance**\n\n"
                f"**Error:** {str(e)}\n\n"
                f"Please try again later.",
                parse_mode='Markdown'
            )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount. Please provide a valid number."
        )

async def reset_confirmations(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset confirmation settings for the user."""
    user_id = update.effective_user.id
    
    if user_id in user_settings:
        user_settings[user_id]['skip_confirmation'] = False
        save_user_settings(user_settings)
        await update.message.reply_text(
            "✅ Confirmation messages have been re-enabled. You will be asked to confirm user creation again."
        )
    else:
        await update.message.reply_text(
            "ℹ️ Confirmation messages are already enabled."
        )

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal. Cleaning up...")
    
    # Run cleanup in event loop if it exists
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(cleanup_browser())
        else:
            asyncio.run(cleanup_browser())
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
    
    sys.exit(0)

def main() -> None:
    """Start the bot."""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Load user contexts and settings from file
    global user_contexts, user_settings
    user_contexts = load_user_contexts()
    user_settings = load_user_settings()
    
    # Create the Application
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear_context", clear_browser_context))
    application.add_handler(CommandHandler("reset_confirmations", reset_confirmations))
    
    # Add callback query handler for buttons
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.REPLY, load_balance))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.REPLY, create_new_user))

    try:
        # Run the bot until the user presses Ctrl-C
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        # Cleanup browser resources
        try:
            import asyncio
            asyncio.run(cleanup_browser())
        except Exception as e:
            logger.error(f"Error during final cleanup: {e}")

if __name__ == "__main__":
    main()