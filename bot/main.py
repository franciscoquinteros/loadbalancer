#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
import signal
import sys
import re
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
        "2. Send 'username amount' to charge balance\n"
        "   Example: `juanperez98 2000`\n\n"
        "Use /help for more information.",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "🆘 **Help - Balance Loader Bot**\n\n"
        "**User Creation:**\n"
        "Send any message with just a username to create a new user.\n"
        "The bot will use the password: `cocos`\n\n"
        "**Balance Loading:**\n"
        "Send a message with format: `username amount`\n"
        "Example: `juanperez98 2000`\n\n"
        "**Examples:**\n"
        "• `juanperez98` (creates user)\n"
        "• `juanperez98 2000` (charges 2000 pesos to juanperez98)\n"
        "• `maria123 500` (charges 500 pesos to maria123)\n\n"
        "**Commands:**\n"
        "• `/start` - Show welcome message\n"
        "• `/help` - Show this help\n"
        "• `/clear_context` - Clear saved browser session\n\n"
        "**Notes:**\n"
        "• All new users get the password: cocos\n"
        "• Browser session is saved to avoid re-login\n"
        "• All usernames and amounts should be in lowercase",
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all text messages - either user creation or balance charging."""
    message_text = update.message.text.strip().lower()
    
    # Check if message contains space (indicating username + amount format)
    if ' ' in message_text:
        # Balance charging format: "username amount"
        parts = message_text.split()
        if len(parts) == 2:
            username = parts[0]
            try:
                amount = int(parts[1])
                await charge_balance(update, context, username, amount)
                return
            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid amount. Please provide a valid number.\n"
                    "Example: `username 2000`"
                )
                return
        else:
            await update.message.reply_text(
                "❌ Invalid format. Use:\n"
                "• `username` (to create user)\n"
                "• `username amount` (to charge balance)"
            )
            return
    else:
        # User creation format: just username
        username = message_text
        
        # Validate username
        if len(username) < 3:
            await update.message.reply_text(
                '❌ Username too short. Please provide a username with at least 3 characters.'
            )
            return
        
        # Validate username contains only valid characters
        if not re.match(r'^[a-z0-9_]+$', username):
            await update.message.reply_text(
                '❌ Invalid username. Use only lowercase letters, numbers, and underscores.'
            )
            return
        
        await create_new_user(update, context, username)

async def create_new_user(update: Update, context: ContextTypes.DEFAULT_TYPE, username: str) -> None:
    """Handle user creation requests."""
    # Fixed password as per requirements
    password = "cocos"
    
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
            # Create Spanish success message that can be copied easily
            success_message = (
                f"Tu usuario ha sido creado 🍀\n\n"
                f"———\n\n"
                f"🔑Usuario: {username}\n"
                f"🔒Contraseña: cocos\n\n"
                f"Enlace: https://cocosbet.com\n\n"
                f"Avisame cuando quieras cargar y te paso el CVU 💫\n\n"
                f"❗️ VA TODO EN MINÚSCULAS, INCLUYENDO LAS PRIMERAS LETRAS ❗️\n\n"
                f"———"
            )
            
            await update.message.reply_text(success_message)
            
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

async def charge_balance(update: Update, context: ContextTypes.DEFAULT_TYPE, username: str, amount: int) -> None:
    """Handle balance charging requests."""
    
    # Send processing message
    processing_message = await update.message.reply_text(
        f"⏳ Charging {amount} pesos to user `{username}`... Please wait.",
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
                f"✅ **Balance charged successfully!**\n\n"
                f"👤 User: `{username}`\n"
                f"💰 Amount: `{amount} pesos`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ **Failed to charge balance**\n\n"
                f"**Error:** {message}\n\n"
                f"Please try again later.",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error charging balance: {e}")
        
        # Try to delete the processing message even if an error occurred
        try:
            await processing_message.delete()
        except Exception as delete_error:
            logger.warning(f"Could not delete processing message: {delete_error}")
            
        await update.message.reply_text(
            f"❌ **An error occurred while charging balance**\n\n"
            f"**Error:** {str(e)}\n\n"
            f"Please try again later.",
            parse_mode='Markdown'
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
    
    # Load user contexts from file
    global user_contexts
    user_contexts = load_user_contexts()
    
    # Create the Application
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear_context", clear_browser_context))
    
    # Add message handler for all text messages (not commands)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

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