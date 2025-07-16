#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import asyncio
import logging
from dotenv import load_dotenv
from playwright.async_api import async_playwright

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

async def login_to_platform(page):
    """Login to the platform with admin credentials"""
    try:
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
        
        # Check if login was successful
        # This will depend on the specific platform's behavior after login
        # For example, checking for a dashboard element or a welcome message
        
        return True
    except Exception as e:
        logger.error(f"Error during login: {e}")
        return False

async def create_user(username, password):
    """Create a new user on the platform"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Set to True in production
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Login to the platform
            login_success = await login_to_platform(page)
            if not login_success:
                logger.error("Failed to login to the platform")
                return False
            
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
            
            # Wait for navigation to complete
            await page.wait_for_load_state("networkidle")        
            # Check if user creation was successful
            # This will depend on the specific platform's behavior after user creation
            # For example, checking for a success message or a redirect
            
            # For demonstration purposes, we'll assume success if no error occurs
            logger.info(f"User {username} created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
        finally:
            await browser.close()

async def assign_balance(username, amount):
    """Assign balance to a user on the platform"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set to True in production
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Login to the platform
            login_success = await login_to_platform(page)
            if not login_success:
                logger.error("Failed to login to the platform")
                return False

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

                            # Wait for navigation to complete
                            await page.wait_for_load_state("networkidle")

                            logger.info(f"Balance {amount} assigned to user {username} successfully")
                            return True
                        else:
                            return False
                        break
            
            if not user_found:
                logger.error(f"User {username} not found in search results")
                return False
            
            
            # For demonstration purposes, we'll assume success if no error occurs
            logger.info(f"Balance {amount} assigned to user {username} successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error assigning balance: {e}")
            return False
        finally:
            await browser.close()