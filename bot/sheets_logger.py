#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import gspread
from google.auth import exceptions
from datetime import datetime
import asyncio
from functools import wraps
import json

# Enable logging
logger = logging.getLogger(__name__)

# Global variables for Google Sheets
_gc = None
_spreadsheet = None

def async_retry(max_retries=3, delay=1):
    """Decorator for retrying async functions with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed after {max_retries} attempts: {e}")
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay * (2 ** attempt)} seconds...")
                    await asyncio.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator

async def init_sheets_client():
    """Initialize Google Sheets client with service account authentication"""
    global _gc, _spreadsheet

    try:
        # Get environment variables
        spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID")
        credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
        credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")  # For Railway/cloud deployment

        if not spreadsheet_id:
            logger.error("GOOGLE_SHEETS_ID environment variable not set")
            return False

        # Try to authenticate using JSON string first (Railway/cloud)
        if credentials_json:
            try:
                logger.info("Using GOOGLE_CREDENTIALS_JSON from environment variable")
                credentials_dict = json.loads(credentials_json)
                _gc = gspread.service_account_from_dict(credentials_dict)
                _spreadsheet = _gc.open_by_key(spreadsheet_id)
                logger.info("Google Sheets client initialized successfully from JSON env var")
                return True
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in GOOGLE_CREDENTIALS_JSON: {e}")
                return False

        # Fallback to file-based authentication (local development)
        if not credentials_path:
            logger.error("Neither GOOGLE_CREDENTIALS_JSON nor GOOGLE_CREDENTIALS_PATH is set")
            return False

        if not os.path.exists(credentials_path):
            logger.error(f"Google credentials file not found: {credentials_path}")
            return False

        logger.info(f"Using credentials file: {credentials_path}")
        _gc = gspread.service_account(filename=credentials_path)
        _spreadsheet = _gc.open_by_key(spreadsheet_id)

        logger.info("Google Sheets client initialized successfully from file")
        return True

    except exceptions.GoogleAuthError as e:
        logger.error(f"Google authentication error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error initializing Google Sheets client: {e}")
        return False

async def get_spreadsheet():
    """Get or initialize the spreadsheet"""
    global _gc, _spreadsheet
    
    if _spreadsheet is None:
        success = await init_sheets_client()
        if not success:
            return None
    
    return _spreadsheet

@async_retry(max_retries=3, delay=1)
async def log_user_creation(username: str, operator: str):
    """Log user creation to Sheet1"""
    try:
        spreadsheet = await get_spreadsheet()
        if not spreadsheet:
            logger.error("Failed to get spreadsheet for user creation logging")
            return False
        
        # Get or create Sheet1
        try:
            sheet1 = spreadsheet.worksheet("New Users")
        except gspread.WorksheetNotFound:
            logger.info("Creating 'New Users' sheet")
            sheet1 = spreadsheet.add_worksheet(title="New Users", rows="1000", cols="10")
            # Add headers
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: sheet1.append_row(["Timestamp", "Username", "Operator"], table_range='A1')
            )
        
        # Prepare data
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_data = [timestamp, username, operator]
        
        # Append row (run in executor to avoid blocking)
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: sheet1.append_row(row_data, table_range='A1')
        )
        
        logger.info(f"Logged user creation: {username} by {operator}")
        return True
        
    except Exception as e:
        logger.error(f"Error logging user creation: {e}")
        raise

@async_retry(max_retries=3, delay=1)
async def log_chip_load(username: str, operator: str, amount: int, bonus_percentage: int = None, load_type: str = "normal"):
    """Log chip load to Sheet2"""
    try:
        spreadsheet = await get_spreadsheet()
        if not spreadsheet:
            logger.error("Failed to get spreadsheet for chip load logging")
            return False
        
        # Get or create Sheet2
        try:
            sheet2 = spreadsheet.worksheet("Chip Loads")
        except gspread.WorksheetNotFound:
            logger.info("Creating 'Chip Loads' sheet")
            sheet2 = spreadsheet.add_worksheet(title="Chip Loads", rows="1000", cols="10")
            # Add headers
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: sheet2.append_row(["Timestamp", "Username", "Operator", "Amount", "Bonus %", "Type"], table_range='A1')
            )
        
        # Prepare data
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bonus_str = str(bonus_percentage) if bonus_percentage is not None else ""
        row_data = [timestamp, username, operator, amount, bonus_str, load_type]
        
        # Append row (run in executor to avoid blocking)
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: sheet2.append_row(row_data, table_range='A1')
        )
        
        logger.info(f"Logged chip load: {amount} chips to {username} by {operator} (type: {load_type})")
        return True
        
    except Exception as e:
        logger.error(f"Error logging chip load: {e}")
        raise

async def test_sheets_connection():
    """Test Google Sheets connection"""
    try:
        spreadsheet = await get_spreadsheet()
        if not spreadsheet:
            return False, "Failed to initialize spreadsheet"
        
        # Try to get spreadsheet info
        info = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: {
                'title': spreadsheet.title,
                'id': spreadsheet.id,
                'url': spreadsheet.url
            }
        )
        
        return True, f"Connected to: {info['title']}"
        
    except Exception as e:
        return False, f"Connection test failed: {str(e)}"

def get_operator_name(update):
    """Extract operator name from Telegram update"""
    try:
        user = update.effective_user
        if user:
            # Try to get username first, fall back to display name
            if user.username:
                return f"@{user.username}"
            else:
                # Use first name and last name if available
                name_parts = []
                if user.first_name:
                    name_parts.append(user.first_name)
                if user.last_name:
                    name_parts.append(user.last_name)
                
                if name_parts:
                    return " ".join(name_parts)
                else:
                    return f"User{user.id}"
        else:
            return "Unknown"
    except Exception as e:
        logger.error(f"Error getting operator name: {e}")
        return "Unknown" 