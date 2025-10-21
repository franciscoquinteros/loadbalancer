#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
import signal
import sys
import re
import asyncio
import math
import subprocess
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from browser_automation import create_user, assign_balance, cleanup_browser
from sheets_logger import log_user_creation, log_chip_load, test_sheets_connection, get_operator_name
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
AWAITING_USERNAME, AWAITING_BALANCE, AWAITING_PASSWORD = range(3)

# File to store user contexts
CONTEXT_FILE = 'user_contexts.json'

# Concurrent operation tracking
active_operations = set()
operation_lock = asyncio.Lock()

# Authentication password from environment
AUTH_PASSWORD = os.getenv("BOT_AUTH_PASSWORD", "defaultpassword123")

# Platform configuration
PLATFORM_URL = os.getenv("PLATFORM_URL", "https://yourplatform.com")
PLATFORM_NAME = os.getenv("PLATFORM_NAME", "YourPlatform")

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

def is_user_authenticated(user_id):
    """Check if user is authenticated"""
    return user_contexts.get(user_id, {}).get('authenticated', False)

def authenticate_user(user_id, username):
    """Mark user as authenticated"""
    if user_id not in user_contexts:
        user_contexts[user_id] = {}
    user_contexts[user_id]['authenticated'] = True
    user_contexts[user_id]['username'] = username
    save_user_contexts(user_contexts)

def verify_password(password):
    """Verify if the provided password is correct"""
    return password.strip() == AUTH_PASSWORD

async def request_authentication(update: Update) -> None:
    """Request authentication from user"""
    await update.message.reply_text(
        "🔐 **Authentication Required**\n\n"
        "This bot requires authentication to use its services.\n"
        "Please enter the access password:",
        parse_mode='Markdown'
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id
    
    if not is_user_authenticated(user_id):
        await update.message.reply_text(
            "Welcome to the Balance Loader Bot! 👋\n\n"
            "🔐 **Authentication Required**\n\n"
            "To use this bot, you need to authenticate first.\n"
            "Please enter the access password to continue.",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(
        "Welcome back to the Balance Loader Bot! 👋\n\n"
        "This bot automates user creation and balance loading on the platform.\n\n"
        "**How to use:**\n"
        "1. Send a username to create a new user\n"
        "   Example: `juanperez98`\n\n"
        "2. Send 'username amount' to charge balance\n"
        "   Example: `juanperez98 2000`\n\n"
        "3. Send 'username amount b<percentage>' for bonus deposits\n"
        "   Example: `juan100 2000 b30` (2000 + 30% bonus)\n\n"
        "Use /help for more information.",
        parse_mode='Markdown'
    )

async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show debug information for troubleshooting."""
    user_id = update.effective_user.id
    
    if not is_user_authenticated(user_id):
        await request_authentication(update)
        return
    
    # Get environment variables (without showing sensitive values)
    admin_url = os.getenv("ADMIN_LOGIN_URL")
    create_url = os.getenv("CREATE_USER_URL") 
    balance_url = os.getenv("BALANCE_URL")
    admin_user = os.getenv("ADMIN_USERNAME")
    admin_pass = os.getenv("ADMIN_PASSWORD")
    sheets_id = os.getenv("GOOGLE_SHEETS_ID")
    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
    
    debug_info = (
        f"🔧 **Debug Information**\n\n"
        f"**Environment Variables:**\n"
        f"• ADMIN_LOGIN_URL: {'✅ SET' if admin_url else '❌ MISSING'}\n"
        f"• CREATE_USER_URL: {'✅ SET' if create_url else '❌ MISSING'}\n"
        f"• BALANCE_URL: {'✅ SET' if balance_url else '❌ MISSING'}\n"
        f"• ADMIN_USERNAME: {'✅ SET' if admin_user else '❌ MISSING'}\n"
        f"• ADMIN_PASSWORD: {'✅ SET' if admin_pass else '❌ MISSING'}\n"
        f"• GOOGLE_SHEETS_ID: {'✅ SET' if sheets_id else '❌ MISSING'}\n"
        f"• GOOGLE_CREDENTIALS_PATH: {'✅ SET' if creds_path else '❌ MISSING'}\n\n"
        f"**URLs (if set):**\n"
        f"• Login: `{admin_url[:50] + '...' if admin_url and len(admin_url) > 50 else admin_url or 'NOT SET'}`\n"
        f"• Create User: `{create_url[:50] + '...' if create_url and len(create_url) > 50 else create_url or 'NOT SET'}`\n"
        f"• Balance: `{balance_url[:50] + '...' if balance_url and len(balance_url) > 50 else balance_url or 'NOT SET'}`\n\n"
        f"**Status:**\n"
        f"• Active operations: {len(active_operations)}\n"
        f"• Browser context exists: {'✅' if Path('browser_context/state.json').exists() else '❌'}\n\n"
        f"**Troubleshooting:**\n"
        f"• If environment variables are missing, check your `.env` file\n"
        f"• Use `/clear_context` to reset browser session if login fails\n"
        f"• Use `/test_sheets` to test Google Sheets connection\n"
        f"• Check logs for detailed error messages"
    )
    
    await update.message.reply_text(debug_info, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    user_id = update.effective_user.id
    
    if not is_user_authenticated(user_id):
        await update.message.reply_text(
            "🔐 **Authentication Required**\n\n"
            "You need to authenticate before accessing help.\n"
            "Please enter the access password to continue.",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(
        "🆘 Help - Balance Loader Bot\n\n"
        "Authentication:\n"
        "• First-time users must enter the access password\n"
        "• Once authenticated, you can use all features\n"
        "• Authentication is saved and persistent\n\n"
        "User Creation:\n"
        "Send any message with just a username to create a new user.\n"
        "The bot will use the password: Roma123\n\n"
        "Balance Loading:\n"
        "Send a message with format: username amount\n"
        "Example: juanperez98 2000\n\n"
        "Bonus Deposit:\n"
        "Send a message with format: username amount b<percentage>\n"
        "Example: juan100 2000 b30 (loads 2000 + 30% bonus = 600 extra)\n\n"
        "Examples:\n"
        "• juanperez98 (creates user)\n"
        "• juanperez98 2000 (charges 2000 pesos to juanperez98)\n"
        "• maria123 500 (charges 500 pesos to maria123)\n"
        "• juan100 2000 b30 (charges 2000 + 600 bonus chips)\n"
        "• player1 1000 b50 (charges 1000 + 500 bonus chips)\n\n"
        "Commands:\n"
        "• /start - Show welcome message\n"
        "• /help - Show this help\n"
        "• /logout - Remove authentication (requires re-authentication)\n"
        "• /clear_context - Clear saved browser session\n"
        "• /status - Show bot performance stats\n"
        "• /debug - Show troubleshooting information\n"
        "• /restart - Restart the bot service\n\n"
        "Notes:\n"
        "• All new users get the password: Roma123\n"
        "• Browser session is saved to avoid re-login\n"
        "• All usernames and amounts should be in lowercase\n"
        "• Bonus deposits are made as two separate transactions\n"
        "• Bonus amount is calculated using floor(base_amount * percentage/100)\n"
        "• Multiple requests are processed concurrently for maximum speed"
    )

async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove user authentication."""
    user_id = update.effective_user.id
    
    if user_id in user_contexts:
        user_contexts[user_id]['authenticated'] = False
        save_user_contexts(user_contexts)
        await update.message.reply_text(
            "🔓 **Logged out successfully**\n\n"
            "You will need to authenticate again to use the bot.\n"
            "Send any message to enter your password.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "ℹ️ You were not authenticated.",
            parse_mode='Markdown'
        )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot performance and status information."""
    user_id = update.effective_user.id
    
    if not is_user_authenticated(user_id):
        await request_authentication(update)
        return
    
    active_count = len(active_operations)
    await update.message.reply_text(
        f"🚀 **Bot Status**\n\n"
        f"⚡ Active operations: {active_count}\n"
        f"🔧 Performance mode: Ultra-Fast\n"
        f"🌐 Browser session: Persistent\n"
        f"💨 Speed optimization: Maximum\n\n"
        f"✅ Ready for requests!",
        parse_mode='Markdown'
    )

async def clear_browser_context(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear the saved browser context."""
    user_id = update.effective_user.id
    
    if not is_user_authenticated(user_id):
        await request_authentication(update)
        return
    
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

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle password verification."""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)
    password = update.message.text.strip()
    
    if verify_password(password):
        authenticate_user(user_id, username)
        await update.message.reply_text(
            "✅ **Authentication successful!**\n\n"
            "You now have access to the Balance Loader Bot.\n"
            "Send /start to see available commands.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ **Invalid password**\n\n"
            "Please try again with the correct access password.",
            parse_mode='Markdown'
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all text messages - either user creation, balance charging, or bonus deposit."""
    message_text = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Check if user is authenticated
    if not is_user_authenticated(user_id):
        # Treat message as password attempt
        await handle_password(update, context)
        return
    
    # Process message as lowercase for bot operations
    message_text = message_text.lower()
    
    # Create unique operation ID for tracking
    operation_id = f"{user_id}_{asyncio.get_event_loop().time()}"

    # Check if message contains space (indicating username + amount format)
    if ' ' in message_text:
        parts = message_text.split()
        
        # Check for bonus deposit format: "username amount b<percentage>"
        if len(parts) == 3 and parts[2].startswith('b') and parts[2][1:].isdigit():
            username = parts[0]
            try:
                base_amount = int(parts[1])
                bonus_percentage = int(parts[2][1:])  # Extract percentage from "b30" -> 30
                
                # Validate bonus percentage (reasonable range)
                if bonus_percentage < 1 or bonus_percentage > 200:
                    await update.message.reply_text(
                        "❌ Invalid bonus percentage. Please use a value between 1 and 200.\n"
                        "Example: `username 2000 b30` (30% bonus)"
                    )
                    return
                
                # Process bonus deposit concurrently
                asyncio.create_task(charge_balance_with_bonus_concurrent(update, context, username, base_amount, bonus_percentage, operation_id))
                return
            except ValueError:
                await update.message.reply_text(
                    "❌ Invalid amount or bonus format. Please provide valid numbers.\n"
                    "Example: `username 2000 b30`"
                )
                return
                
        # Regular balance charging format: "username amount"
        elif len(parts) == 2:
            username = parts[0]
            try:
                amount = int(parts[1])
                # Process charge balance concurrently
                asyncio.create_task(charge_balance_concurrent(update, context, username, amount, operation_id))
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
                "• `username amount` (to charge balance)\n"
                "• `username amount b<percentage>` (to charge with bonus)"
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
        
        # Process user creation concurrently
        asyncio.create_task(create_new_user_concurrent(update, context, username, operation_id))

async def create_new_user_concurrent(update: Update, context: ContextTypes.DEFAULT_TYPE, username: str, operation_id: str) -> None:
    """Handle user creation requests with concurrent processing."""
    async with operation_lock:
        active_operations.add(operation_id)
    
    try:
        # Fixed password as per requirements
        password = "Roma123"
        
        # Send processing message instantly
        processing_message = await update.message.reply_text(
            f"⚡ Creating user `{username}`...",
            parse_mode='Markdown'
        )
        
        try:
            # Call the browser automation function to create the user
            success, message = await create_user(username, password)
            
            # Delete processing message immediately
            await processing_message.delete()
            
            if success:
                # Log to Google Sheets
                try:
                    operator = get_operator_name(update)
                    await log_user_creation(username, operator)
                    logger.info(f"User creation logged to Google Sheets: {username} by {operator}")
                except Exception as e:
                    logger.error(f"Failed to log user creation to Google Sheets: {e}")
                    # Continue with success message even if logging fails
                
                # Create Spanish success message that can be copied easily
                copyable_message = (
                    f"🔑Usuario: {username}\n"
                    f"🔒Contraseña: Roma123\n\n"
                    f"❗️VA TODO EN MINÚSCULAS, INCLUYENDO LAS PRIMERAS LETRAS❗️\n\n"
                    f"👉Enlace: {PLATFORM_URL}\n\n"
                    f"Te dejo el CVU aqui abajo para cuando quieras cargar 👇\n\n"
                )
                
                # Send the message in a code block to make it easily copyable
                await update.message.reply_text(
                    f"Tu usuario ha sido creado 🍀\n\n"
                    f"```\n{copyable_message}\n```", 
                    parse_mode='Markdown'
                )
                
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
            except:
                pass
                
            await update.message.reply_text(
                f"❌ **An error occurred while creating the user**\n\n"
                f"Please try again with different username.",
                parse_mode='Markdown'
            )
    finally:
        async with operation_lock:
            active_operations.discard(operation_id)

async def charge_balance_concurrent(update: Update, context: ContextTypes.DEFAULT_TYPE, username: str, amount: int, operation_id: str) -> None:
    """Handle balance charging requests with concurrent processing."""
    async with operation_lock:
        active_operations.add(operation_id)
    
    try:
        # Send processing message instantly
        processing_message = await update.message.reply_text(
            f"⚡ Charging {amount} pesos to `{username}`...",
            parse_mode='Markdown'
        )
        
        try:
            # Call the browser automation function to assign balance
            success, message = await assign_balance(username, amount)
            
            # Delete processing message immediately
            await processing_message.delete()
            
            if success:
                # Log to Google Sheets
                try:
                    operator = get_operator_name(update)
                    await log_chip_load(username, operator, amount, None, "normal")
                    logger.info(f"Chip load logged to Google Sheets: {amount} to {username} by {operator}")
                except Exception as e:
                    logger.error(f"Failed to log chip load to Google Sheets: {e}")
                    # Continue with success message even if logging fails
                
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
            except:
                pass
                
            await update.message.reply_text(
                f"❌ **An error occurred while charging balance**\n\n"
                f"**Error:** {str(e)}\n\n"
                f"Please try again later.",
                parse_mode='Markdown'
            )
    finally:
        async with operation_lock:
            active_operations.discard(operation_id)

async def charge_balance_with_bonus_concurrent(update: Update, context: ContextTypes.DEFAULT_TYPE, username: str, base_amount: int, bonus_percentage: int, operation_id: str) -> None:
    """Handle balance charging with bonus deposit - two separate transactions."""
    async with operation_lock:
        active_operations.add(operation_id)
    
    try:
        # Calculate bonus amount using floor
        bonus_amount = math.floor(base_amount * (bonus_percentage / 100))
        
        # Send processing message instantly
        processing_message = await update.message.reply_text(
            f"⚡ Loading {base_amount} chips + {bonus_percentage}% bonus to `{username}`...",
            parse_mode='Markdown'
        )
        
        try:
            # First transaction: Base amount
            success1, message1 = await assign_balance(username, base_amount)
            
            if not success1:
                # Delete processing message
                await processing_message.delete()
                await update.message.reply_text(
                    f"❌ **Failed to load base amount**\n\n"
                    f"**Error:** {message1}\n\n"
                    f"Please try again later.",
                    parse_mode='Markdown'
                )
                return
            
            # Second transaction: Bonus amount
            success2, message2 = await assign_balance(username, bonus_amount)
            
            # Delete processing message
            await processing_message.delete()
            
            if success2:
                # Both transactions successful - log both to Google Sheets
                try:
                    operator = get_operator_name(update)
                    # Log base amount
                    await log_chip_load(username, operator, base_amount, None, "normal")
                    # Log bonus amount
                    await log_chip_load(username, operator, bonus_amount, bonus_percentage, "bonus")
                    logger.info(f"Bonus deposit logged to Google Sheets: {base_amount} + {bonus_amount} bonus to {username} by {operator}")
                except Exception as e:
                    logger.error(f"Failed to log bonus deposit to Google Sheets: {e}")
                    # Continue with success message even if logging fails
                
                # Both transactions successful
                await update.message.reply_text(
                    f"✅ {base_amount} chips loaded to {username}.\n"
                    f"✅ {bonus_amount}‑chip bonus ({bonus_percentage}%) loaded.\n"
                    f"Good luck!",
                    parse_mode='Markdown'
                )
            else:
                # Base succeeded but bonus failed - log only the base amount
                try:
                    operator = get_operator_name(update)
                    # Log only the successful base amount
                    await log_chip_load(username, operator, base_amount, None, "normal")
                    logger.info(f"Partial bonus deposit logged to Google Sheets: {base_amount} to {username} by {operator} (bonus failed)")
                except Exception as e:
                    logger.error(f"Failed to log partial bonus deposit to Google Sheets: {e}")
                    # Continue with error message even if logging fails
                
                # Base succeeded but bonus failed
                await update.message.reply_text(
                    f"✅ {base_amount} chips loaded to {username}.\n"
                    f"❌ **Bonus deposit failed:** {message2}\n\n"
                    f"Base amount was loaded successfully, but bonus deposit encountered an error.",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error in bonus deposit: {e}")
            
            # Try to delete the processing message even if an error occurred
            try:
                await processing_message.delete()
            except:
                pass
                
            await update.message.reply_text(
                f"❌ **An error occurred during bonus deposit**\n\n"
                f"**Error:** {str(e)}\n\n"
                f"Please try again later.",
                parse_mode='Markdown'
            )
    finally:
        async with operation_lock:
            active_operations.discard(operation_id)

async def test_login_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test login functionality without performing any operations."""
    user_id = update.effective_user.id
    
    if not is_user_authenticated(user_id):
        await request_authentication(update)
        return
    
    from browser_automation import get_browser_context, login_to_platform
    
    processing_message = await update.message.reply_text("🔍 Testing login...")
    
    try:
        # Get browser context
        browser_context = await get_browser_context()
        page = await browser_context.new_page()
        
        try:
            # Test login
            login_success = await login_to_platform(page)
            
            if login_success:
                await processing_message.edit_text(
                    "✅ **Login test successful!**\n\n"
                    "The bot can successfully log into the platform.\n"
                    "You can now create users and charge balances.",
                    parse_mode='Markdown'
                )
            else:
                await processing_message.edit_text(
                    "❌ **Login test failed!**\n\n"
                    "Please check:\n"
                    "• Your `.env` file has correct credentials\n"
                    "• Platform URLs are accessible\n"
                    "• Admin credentials are valid\n"
                    "• Use `/debug` for more information",
                    parse_mode='Markdown'
                )
        finally:
            await page.close()
            
    except Exception as e:
        logger.error(f"Error in login test: {e}")
        await processing_message.edit_text(
            f"❌ **Login test error:**\n\n"
            f"`{str(e)}`\n\n"
            f"Use `/debug` for troubleshooting information.",
            parse_mode='Markdown'
        )

async def test_sheets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test Google Sheets connection."""
    user_id = update.effective_user.id
    
    if not is_user_authenticated(user_id):
        await request_authentication(update)
        return
    
    processing_message = await update.message.reply_text("🔍 Testing Google Sheets connection...")
    
    try:
        success, message = await test_sheets_connection()
        
        if success:
            await processing_message.edit_text(
                f"✅ **Google Sheets test successful!**\n\n"
                f"{message}\n\n"
                f"The bot can log operations to Google Sheets.",
                parse_mode='Markdown'
            )
        else:
            await processing_message.edit_text(
                f"❌ **Google Sheets test failed!**\n\n"
                f"{message}\n\n"
                f"Please check:\n"
                f"• GOOGLE_SHEETS_ID environment variable\n"
                f"• GOOGLE_CREDENTIALS_PATH environment variable\n"
                f"• Google service account credentials file\n"
                f"• Spreadsheet sharing permissions",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error in Google Sheets test: {e}")
        await processing_message.edit_text(
            f"❌ **Google Sheets test error:**\n\n"
            f"`{str(e)}`\n\n"
            f"Check logs for detailed error information.",
            parse_mode='Markdown'
        )

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Restart the bot by restarting the systemd service."""
    user_id = update.effective_user.id
    
    if not is_user_authenticated(user_id):
        await request_authentication(update)
        return
    
    try:
        # Send confirmation message first
        await update.message.reply_text(
            "🔄 **Restarting bot...**\n\n"
            "The bot will restart in a few seconds. Please wait.",
            parse_mode='Markdown'
        )
        
        logger.info(f"Bot restart requested by user {user_id}")
        
        # Schedule restart after a short delay to allow message to be sent
        async def delayed_restart():
            await asyncio.sleep(2)  # Give time for message to be sent
            try:
                service_name = os.getenv("TELEGRAM_BOT_SERVICE_NAME", "balanceloader.service")
                subprocess.run(["sudo", "systemctl", "restart", service_name], check=True)
            except Exception as e:
                logger.error(f"Error during delayed restart: {e}")
        
        # Schedule the restart to happen after responding
        asyncio.create_task(delayed_restart())
        
    except Exception as e:
        logger.error(f"Error in restart_command: {e}")
        await update.message.reply_text(
            f"❌ **An unexpected error occurred during restart:**\n\n"
            f"`{str(e)}`\n\n"
            f"Please try again or check logs.",
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
    
    # Create the Application with optimized settings
    application = (Application.builder()
                  .token(os.getenv("TELEGRAM_BOT_TOKEN"))
                  .concurrent_updates(True)  # Enable concurrent update processing
                  .build())

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("logout", logout_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("clear_context", clear_browser_context))
    application.add_handler(CommandHandler("debug", debug_command))
    application.add_handler(CommandHandler("test_login", test_login_command))
    application.add_handler(CommandHandler("test_sheets", test_sheets_command))
    application.add_handler(CommandHandler("restart", restart_command)) # Add restart command handler
    
    # Add message handler for all text messages (not commands)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    try:
        # Run the bot until the user presses Ctrl-C
        logger.info("Starting bot with ultra-fast performance optimizations...")
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