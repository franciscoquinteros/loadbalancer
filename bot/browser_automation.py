#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import asyncio
import logging
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from pathlib import Path

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get environment variables
ADMIN_LOGIN_URL = os.getenv("ADMIN_LOGIN_URL")
CREATE_USER_URL = os.getenv("CREATE_USER_URL")
BALANCE_URL = os.getenv("BALANCE_URL")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# Path to store browser context
BROWSER_CONTEXT_PATH = Path("browser_context")

# Global browser and context variables
_playwright = None
_browser = None
_context = None

async def get_browser_context():
    """Get or create a persistent browser context"""
    global _playwright, _browser, _context
    
    if _playwright is None or _browser is None or _context is None:
        _playwright = await async_playwright().__aenter__()
        
        # Create browser context directory if it doesn't exist
        BROWSER_CONTEXT_PATH.mkdir(exist_ok=True)
        
        # Launch browser
        _browser = await _playwright.chromium.launch(headless=True)
        
        # Try to load existing context, create new one if it doesn't exist
        context_file = BROWSER_CONTEXT_PATH / "state.json"
        try:
            if context_file.exists():
                _context = await _browser.new_context(storage_state=str(context_file))
                logger.info("Loaded existing browser context")
            else:
                _context = await _browser.new_context()
                logger.info("Created new browser context")
        except Exception as e:
            logger.warning(f"Could not load existing context: {e}. Creating new one.")
            _context = await _browser.new_context()
    
    return _context

async def save_browser_context():
    """Save the current browser context state"""
    try:
        if _context is not None:
            context_file = BROWSER_CONTEXT_PATH / "state.json"
            await _context.storage_state(path=str(context_file))
            logger.info("Browser context saved successfully")
    except Exception as e:
        logger.error(f"Error saving browser context: {e}")

async def is_logged_in(page):
    """Check if we're already logged in by looking for login-specific elements"""
    try:
        # Go to the create user page and check if we're redirected to login
        await page.goto(CREATE_USER_URL, wait_until="networkidle")
        
        # If we see a login form, we're not logged in
        login_form = await page.query_selector('input[name="login"]')
        if login_form:
            logger.info("Not logged in - login form detected")
            return False
        
        # If we can see user creation form elements, we're logged in
        username_input = await page.query_selector('input[name="username"]')
        if username_input:
            logger.info("Already logged in - user creation form detected")
            return True
        
        # If neither, assume we need to login
        logger.info("Login status unclear - assuming not logged in")
        return False
        
    except Exception as e:
        logger.error(f"Error checking login status: {e}")
        return False

async def login_to_platform(page):
    """Login to the platform with admin credentials"""
    try:
        # First check if we're already logged in
        if await is_logged_in(page):
            logger.info("Already logged in, skipping login process")
            return True
        
        logger.info("Not logged in, proceeding with login")
        await page.goto(ADMIN_LOGIN_URL)
        
        # Wait for the login form to be visible
        await page.wait_for_selector('input[name="login"]', state="visible")
        await page.wait_for_selector('input[name="password"]', state="visible")
        
        # Fill in the login form
        await page.fill('input[name="login"]', ADMIN_USERNAME)
        await page.fill('input[name="password"]', ADMIN_PASSWORD)
        
        # Click the login button
        await page.click('button[type="submit"]')

        await page.wait_for_selector('.spinner-desktop', state="hidden")
        # Wait a moment for form validation
        await asyncio.sleep(2)
        
        # Wait for navigation to complete
        await page.wait_for_load_state("networkidle")
        
        # Save the context after successful login
        await save_browser_context()
        
        logger.info("Login successful and context saved")
        return True
    except Exception as e:
        logger.error(f"Error during login: {e}")
        return False

async def create_user(username, password):
    """Create a new user on the platform"""
    try:
        context = await get_browser_context()
        page = await context.new_page()
        
        try:
            # Login to the platform (will skip if already logged in)
            login_success = await login_to_platform(page)
            if not login_success:
                error_msg = "Failed to login to the platform"
                logger.error(error_msg)
                return False, error_msg
            
            # Navigate to the create user page
            await page.goto(CREATE_USER_URL)

            await page.wait_for_selector('.spinner-desktop', state="hidden")
            # Wait a moment for form validation
            await asyncio.sleep(2)
            
            # Wait for the create user form to be visible
            await page.wait_for_selector('input[name="username"]', state="visible")
            await page.wait_for_selector('input[name="password"]', state="visible")
            await page.wait_for_selector('input[name="password2"]', state="visible")
            
            # Fill in the form
            await page.fill('input[name="username"]', username)
            await page.fill('input[name="password"]', password)
            await page.fill('input[name="password2"]', password)
            
            # Submit the form
            await page.click('button[type="submit"]')    

            await page.wait_for_selector('.spinner-desktop', state="hidden")
            # Wait a moment for form validation
            await asyncio.sleep(2)
            
            # Check for error notification
            try:
                # Wait for either error notification or success notification
                notification = await page.wait_for_selector(
                    '.notification-desktop.notification-desktop_type_error, .notification-desktop.notification-desktop_type_success',
                    timeout=10000
                )
                
                if notification:
                    # Check if it's an error notification
                    is_error = await notification.evaluate('element => element.classList.contains("notification-desktop_type_error")')
                    is_success = await notification.evaluate('element => element.classList.contains("notification-desktop_type_success")')
                    
                    # Get the notification message text
                    text_element = await notification.query_selector('.notification-desktop__text')
                    if text_element:
                        notification_text = await text_element.text_content()
                        
                        if is_error:
                            error_msg = f"User creation failed: {notification_text}"
                            logger.error(error_msg)
                            return False, error_msg
                        elif is_success:
                            success_msg = f"User created successfully: {notification_text}"
                            logger.info(success_msg)
                            return True, success_msg
                    
            except Exception:
                # No notification found within timeout, check other indicators
                logger.info("No notification found, checking other success indicators")
                pass
            
            # Wait for navigation to complete
            await page.wait_for_load_state("networkidle")        
            
            # Additional check: if we're still on the create user page, it might indicate an error
            current_url = page.url
            if CREATE_USER_URL in current_url:
                # Still on create user page, check if form was cleared (success) or still has values (error)
                username_value = await page.get_attribute('input[name="username"]', 'value')
                if username_value and username_value.strip():
                    error_msg = "User creation failed: Form validation error"
                    logger.error(error_msg)
                    return False, error_msg
            
            logger.info(f"User {username} created successfully")
            return True, "User created successfully"
            
        except Exception as e:
            error_msg = f"Error creating user: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        finally:
            await page.close()
            
    except Exception as e:
        error_msg = f"Error in create_user: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

async def assign_balance(username, amount):
    """Assign balance to a user on the platform"""
    try:
        context = await get_browser_context()
        page = await context.new_page()
        
        try:
            # Login to the platform (will skip if already logged in)
            login_success = await login_to_platform(page)
            if not login_success:
                error_msg = "Failed to login to the platform"
                logger.error(error_msg)
                return False, error_msg
            
            # Navigate to the create user page
            await page.goto(BALANCE_URL)

            await page.wait_for_selector('.spinner-desktop', state="hidden")
            # Wait a moment for form validation
            await asyncio.sleep(2)
            
            # Search for the user
            await page.wait_for_selector('input[name="search"]', state="visible")
            await page.fill('input[name="search"]', username)

            await page.wait_for_selector('.spinner-desktop', state="hidden")
            # Wait a moment for form validation
            await asyncio.sleep(2)

            # Look for the user in search results and click TopUp button
            user_rows = await page.query_selector_all('.table-users-desktop__item')

            user_found = False
            for user_row in user_rows:
                # Check if this row contains the target username
                username_element = await user_row.query_selector('.table-row-users-desktop__td-user-name')
                if username_element:
                    row_username = await username_element.text_content()
                    if row_username and row_username.strip() == username:
                        # Look for the TopUp button in this row
                        topup_button = await user_row.query_selector('.table-row-users-desktop__td-operations-top-up')
                        
                        if topup_button:
                            # Click the TopUp button
                            await topup_button.click()
                            user_found = True
                            
                            # Wait for navigation to deposit form
                            await asyncio.sleep(3)
                            
                            await page.wait_for_selector('.spinner-desktop', state="hidden")
                            # Wait a moment for form validation
                            await asyncio.sleep(3)
                            
                            # Wait for deposit form to load
                            await page.wait_for_selector('.form-deposit-desktop', state="visible")
                            
                            # Find and fill the amount input field
                            await page.wait_for_selector('input[name="amount"]', state="visible")
                            
                            # Clear and fill the amount field
                            await page.fill('input[name="amount"]',"")
                            await page.fill('input[name="amount"]', str(amount))
                            
                            # Wait a moment for form validation
                            await asyncio.sleep(1)
                            
                            # Find and click the deposit button
                            await page.click('button[type="submit"]')

                            # Wait for processing
                            await page.wait_for_selector('.spinner-desktop', state="hidden")
                            await asyncio.sleep(3)

                            # Check for error notification
                            try:
                                # Wait for either error notification or success notification
                                notification = await page.wait_for_selector(
                                    '.notification-desktop.notification-desktop_type_error, .notification-desktop.notification-desktop_type_success',
                                    timeout=10000
                                )
                                
                                if notification:
                                    # Check if it's an error notification
                                    is_error = await notification.evaluate('element => element.classList.contains("notification-desktop_type_error")')
                                    is_success = await notification.evaluate('element => element.classList.contains("notification-desktop_type_success")')
                                    
                                    # Get the notification message text
                                    text_element = await notification.query_selector('.notification-desktop__text')
                                    if text_element:
                                        notification_text = await text_element.text_content()
                                        
                                        if is_error:
                                            error_msg = f"Balance assignment failed: {notification_text}"
                                            logger.error(error_msg)
                                            return False, error_msg
                                        elif is_success:
                                            success_msg = f"Balance assigned successfully: {notification_text}"
                                            logger.info(success_msg)
                                            return True, success_msg
                                    
                            except Exception:
                                # No notification found within timeout, check other indicators
                                logger.info("No notification found for balance assignment, checking other indicators")
                                pass

                            # Wait for navigation to complete
                            await page.wait_for_load_state("networkidle")

                            logger.info(f"Balance {amount} assigned to user {username} successfully")
                            return True, "Balance assigned successfully"
                        else:
                            error_msg = "TopUp button not found for user"
                            logger.error(error_msg)
                            return False, error_msg
                        break
            
            if not user_found:
                error_msg = f"User {username} not found in search results"
                logger.error(error_msg)
                return False, error_msg
            
            
            # For demonstration purposes, we'll assume success if no error occurs
            logger.info(f"Balance {amount} assigned to user {username} successfully")
            return True, "Balance assigned successfully"
            
        except Exception as e:
            error_msg = f"Error assigning balance: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        finally:
            await page.close()
            
    except Exception as e:
        error_msg = f"Error in assign_balance: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

async def cleanup_browser():
    """Cleanup browser resources"""
    global _playwright, _browser, _context
    try:
        if _context is not None:
            await _context.close()
            _context = None
        if _browser is not None:
            await _browser.close()
            _browser = None
        if _playwright is not None:
            await _playwright.__aexit__(None, None, None)
            _playwright = None
        logger.info("Browser resources cleaned up")
    except Exception as e:
        logger.error(f"Error during browser cleanup: {e}")