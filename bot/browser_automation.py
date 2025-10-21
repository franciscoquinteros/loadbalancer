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
        
        # Detect if we're in a headless environment (VPS)
        import sys
        # Use headless mode only on Windows for local testing
        # On Linux/VPS, use non-headless with xvfb
        is_headless = sys.platform == 'win32'
        
        # Launch browser with stealth configuration to avoid anti-bot detection
        _browser = await _playwright.chromium.launch(
            headless=is_headless,  # False on Linux to work with xvfb
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',  # Hide automation
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--no-first-run',
                '--disable-default-apps',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-sync',
                '--disable-translate',
                '--disable-ipc-flooding-protection',
                '--disable-hang-monitor',
                '--disable-prompt-on-repost',
                '--disable-domain-reliability',
                '--disable-component-extensions-with-background-pages',
                '--disable-background-networking',
                '--disable-features=TranslateUI',
                '--no-default-browser-check',
                '--no-pings',
                '--memory-pressure-off',
                '--max_old_space_size=4096'
            ]
        )
        
        # Try to load existing context, create new one if it doesn't exist
        context_file = BROWSER_CONTEXT_PATH / "state.json"
        
        # Context options to appear more like a real browser
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'locale': 'es-AR',
            'timezone_id': 'America/Argentina/Buenos_Aires',
            'permissions': ['geolocation'],
            'extra_http_headers': {
                'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8',
            }
        }
        
        try:
            if context_file.exists():
                _context = await _browser.new_context(storage_state=str(context_file), **context_options)
                logger.info("Loaded existing browser context")
            else:
                _context = await _browser.new_context(**context_options)
                logger.info("Created new browser context")
        except Exception as e:
            logger.warning(f"Could not load existing context: {e}. Creating new one.")
            _context = await _browser.new_context(**context_options)
        
        # Add stealth scripts to hide automation
        await _context.add_init_script("""
            // Override the navigator.webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            
            // Override plugins to match a real browser
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['es-AR', 'es', 'en'],
            });
            
            // Chrome runtime
            window.chrome = {
                runtime: {},
            };
            
            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
    
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

async def reset_browser_context():
    """Reset browser context to handle corrupted or stale sessions"""
    global _context
    try:
        logger.info("Resetting browser context due to login issues")
        
        # Close current context if it exists
        if _context is not None:
            await _context.close()
            _context = None
        
        # Remove saved context file to force fresh start
        context_file = BROWSER_CONTEXT_PATH / "state.json"
        if context_file.exists():
            context_file.unlink()
            logger.info("Removed stale browser context file")
        
        # Create new context
        if _browser is not None:
            _context = await _browser.new_context()
            logger.info("Created fresh browser context")
        
        return True
    except Exception as e:
        logger.error(f"Error resetting browser context: {e}")
        return False

async def is_logged_in(page):
    """Check if we're already logged in by looking for login-specific elements"""
    try:
        logger.info("Checking login status...")
        
        # Navigate to create user page to test access
        logger.info(f"Navigating to: {CREATE_USER_URL}")
        
        # Add retry logic for navigation in case of network issues
        max_nav_attempts = 2
        for attempt in range(max_nav_attempts):
            try:
                await page.goto(CREATE_USER_URL, wait_until="domcontentloaded", timeout=15000)
                break
            except Exception as nav_error:
                if attempt == max_nav_attempts - 1:
                    logger.error(f"Navigation failed after {max_nav_attempts} attempts: {nav_error}")
                    return False
                logger.warning(f"Navigation attempt {attempt + 1} failed: {nav_error}. Retrying...")
                await asyncio.sleep(1.0)
        
        # Wait for page to fully load and stabilize
        await asyncio.sleep(0.8)  # +1 second (was 0.8)
        
        # Check for login form (indicates not logged in)
        login_form = await page.query_selector('input[type="text"][placeholder="Nombre"]')
        if login_form:
            logger.info("Not logged in - login form detected")
            return False
        
        # Check for user creation form (indicates logged in)
        username_input = await page.query_selector('input[type="text"][placeholder="Nombre de usuario"]')
        if username_input:
            logger.info("Already logged in - user creation form detected")
            return True
        
        # If neither found, check page URL and content for more clues
        current_url = page.url
        logger.info(f"Current URL: {current_url}")
        
        # Check if we're redirected to login page
        if "login" in current_url.lower():
            logger.info("Login status: redirected to login page - not logged in")
            return False
        
        # Check if we're on the expected page
        if CREATE_USER_URL in current_url:
            logger.info("Login status: on create user page but no form detected - assuming logged in")
            return True
        
        # Additional check: look for common authentication failure indicators
        auth_error_selectors = [
            '.unauthorized',
            '.auth-error', 
            '.login-required',
            '[data-testid="login-required"]',
            '.error-401'
        ]
        
        for selector in auth_error_selectors:
            error_element = await page.query_selector(selector)
            if error_element:
                logger.info(f"Authentication error indicator found: {selector} - not logged in")
                return False
        
        # Check page title for authentication indicators
        try:
            page_title = await page.title()
            if page_title and any(word in page_title.lower() for word in ['login', 'sign in', 'authentication', 'unauthorized']):
                logger.info(f"Page title indicates not logged in: {page_title}")
                return False
        except Exception:
            pass
        
        # Default to not logged in for safety
        logger.info("Login status unclear - assuming not logged in for safety")
        return False
        
    except Exception as e:
        logger.error(f"Error checking login status: {e}")
        import traceback
        logger.error(f"Login check traceback: {traceback.format_exc()}")
        return False

async def login_to_platform(page):
    """Login to the platform with admin credentials"""
    max_login_attempts = 2
    current_page = page
    
    for attempt in range(max_login_attempts):
        try:
            logger.info(f"Login attempt {attempt + 1}/{max_login_attempts}")
            
            # First check if we're already logged in
            if await is_logged_in(current_page):
                logger.info("Already logged in, skipping login process")
                return True, current_page
            
            logger.info("Not logged in, proceeding with login")
            
            # Validate environment variables
            if not ADMIN_LOGIN_URL or not ADMIN_USERNAME or not ADMIN_PASSWORD:
                logger.error("Missing login credentials in environment variables")
                logger.error(f"ADMIN_LOGIN_URL: {'SET' if ADMIN_LOGIN_URL else 'MISSING'}")
                logger.error(f"ADMIN_USERNAME: {'SET' if ADMIN_USERNAME else 'MISSING'}")
                logger.error(f"ADMIN_PASSWORD: {'SET' if ADMIN_PASSWORD else 'MISSING'}")
                return False, current_page
            
            # Navigate with moderate waiting for better reliability
            logger.info(f"Navigating to login URL: {ADMIN_LOGIN_URL}")
            await current_page.goto(ADMIN_LOGIN_URL, wait_until="domcontentloaded")
            
            # Wait a bit longer for login form to be ready
            await asyncio.sleep(0.5)  # +1 second (was 0.5)
            
            # Check if login form is present
            login_input_present = await current_page.query_selector('input[type="text"][placeholder="Nombre"]')
            password_input_present = await current_page.query_selector('input[type="password"]')
            submit_button_present = await current_page.query_selector('button:has-text("Acceder")')
            
            if not login_input_present:
                logger.error("Login input field not found on page")
                if attempt < max_login_attempts - 1:
                    logger.info("Retrying with fresh context...")
                    await current_page.close()
                    await reset_browser_context()
                    current_page = await (await get_browser_context()).new_page()
                    continue
                return False, current_page
            if not password_input_present:
                logger.error("Password input field not found on page")
                if attempt < max_login_attempts - 1:
                    logger.info("Retrying with fresh context...")
                    await current_page.close()
                    await reset_browser_context()
                    current_page = await (await get_browser_context()).new_page()
                    continue
                return False, current_page
            if not submit_button_present:
                logger.error("Submit button not found on page")
                if attempt < max_login_attempts - 1:
                    logger.info("Retrying with fresh context...")
                    await current_page.close()
                    await reset_browser_context()
                    current_page = await (await get_browser_context()).new_page()
                    continue
                return False, current_page
            
            logger.info("Login form elements found, proceeding with form filling")
            
            # Use more reliable selector-based approach with form clearing
            try:
                # Clear and fill login field - this prevents issues with cached/overlapping values
                await current_page.fill('input[type="text"][placeholder="Nombre"]', '')  # Clear first
                await asyncio.sleep(0.1)  # +1 second (was 0.1)
                await current_page.fill('input[type="text"][placeholder="Nombre"]', ADMIN_USERNAME)
                await asyncio.sleep(0.1)  # +1 second (was 0.1)

                # Clear and fill password field - this prevents issues with cached/overlapping values
                await current_page.fill('input[type="password"]', '')  # Clear first
                await asyncio.sleep(0.1)  # +1 second (was 0.1)
                await current_page.fill('input[type="password"]', ADMIN_PASSWORD)
                await asyncio.sleep(0.5)  # +1 second (was 0.5)

                # Submit the form
                await current_page.click('button[type="button"].button.button_sizable_default.button_colors_default')
                logger.info("Login form submitted")
                
            except Exception as e:
                logger.error(f"Error filling login form: {e}")
                if attempt < max_login_attempts - 1:
                    logger.info("Retrying with fresh context...")
                    await current_page.close()
                    await reset_browser_context()
                    current_page = await (await get_browser_context()).new_page()
                    continue
                return False, current_page
            
            # Wait for login processing with reasonable timeout
            await asyncio.sleep(0.6)  # Reduced from 1.0s for speed
            
            # Check for login success by looking for redirect or success indicators
            try:
                # Try navigating to create user page to test login
                await current_page.goto(CREATE_USER_URL, wait_until="domcontentloaded")
                await asyncio.sleep(0.5)  # +1 second (was 0.5)
                
                # Check if we can see user creation form (indicates successful login)
                username_input = await current_page.query_selector('input[type="text"][placeholder="Nombre de usuario"]')
                if username_input:
                    # Save context in background
                    asyncio.create_task(save_browser_context())
                    logger.info("Login successful - user creation form accessible")
                    return True, current_page
                else:
                    # Check if we're still on login page (indicates failed login)
                    login_form = await current_page.query_selector('input[type="text"][placeholder="Nombre"]')
                    if login_form:
                        logger.error(f"Login failed - still on login page (attempt {attempt + 1})")
                        # Try to get error message if available
                        try:
                            error_element = await current_page.query_selector('.error, .alert, .notification-desktop_type_error')
                            if error_element:
                                error_text = await error_element.text_content()
                                logger.error(f"Login error message: {error_text}")
                        except Exception:
                            pass
                        
                        # If this is not the last attempt, reset context and retry
                        if attempt < max_login_attempts - 1:
                            logger.info("Resetting browser context and retrying login...")
                            await current_page.close()
                            await reset_browser_context()
                            current_page = await (await get_browser_context()).new_page()
                            continue
                        return False, current_page
                    else:
                        logger.warning("Login status unclear - proceeding with caution")
                        return True, current_page
                        
            except Exception as e:
                logger.error(f"Error checking login success: {e}")
                if attempt < max_login_attempts - 1:
                    logger.info("Retrying with fresh context...")
                    await current_page.close()
                    await reset_browser_context()
                    current_page = await (await get_browser_context()).new_page()
                    continue
                return False, current_page
            
        except Exception as e:
            logger.error(f"Error during login attempt {attempt + 1}: {e}")
            import traceback
            logger.error(f"Login traceback: {traceback.format_exc()}")
            
            # If this is not the last attempt, reset context and retry
            if attempt < max_login_attempts - 1:
                logger.info("Resetting browser context and retrying login...")
                await current_page.close()
                await reset_browser_context()
                current_page = await (await get_browser_context()).new_page()
                continue
            return False, current_page
    
    # If we've exhausted all attempts
    logger.error(f"Login failed after {max_login_attempts} attempts")
    return False, current_page

async def create_user(username, password):
    """Create a new user on the platform"""
    try:
        context = await get_browser_context()
        page = await context.new_page()
        
        try:
            # Login to the platform (will skip if already logged in)
            login_success, page = await login_to_platform(page)
            if not login_success:
                error_msg = "Failed to login to the platform"
                logger.error(error_msg)
                return False, error_msg
            
            # Navigate with minimal waiting
            await page.goto(CREATE_USER_URL, wait_until="domcontentloaded")

            # Wait for page to be ready
            await asyncio.sleep(0.2)  # Reduced from 0.3s for speed

            # Check if form elements are present
            username_input = await page.query_selector('input[type="text"][placeholder="Nombre de usuario"]')
            password_input = await page.query_selector('input[name="password"]')
            password2_input = await page.query_selector('input[name="confirmPassword"]')
            submit_button = await page.query_selector('button[type="submit"]')

            if not username_input or not password_input or not password2_input or not submit_button:
                error_msg = "User creation form elements not found on page"
                logger.error(error_msg)
                return False, error_msg

            logger.info(f"Creating user {username} with form submission")
            
            # NOTE: No request interception - let browser handle everything naturally
            # Request interception triggers ServicePipe anti-bot detection

            # Fill form fields with human-like delays (+1 second to each delay)
            # Use type() instead of fill() to trigger React/Vue state updates
            username_input = await page.query_selector('input[type="text"][placeholder="Nombre de usuario"]')
            if username_input:
                await username_input.click()  # Focus the input
                await asyncio.sleep(0.15)  # Reduced for speed
                await username_input.fill('')  # Clear first
                await asyncio.sleep(0.1)  # Reduced for speed
                # Type faster
                await username_input.type(username, delay=50)
                logger.info(f"Username field filled: {username}")
                await asyncio.sleep(0.3)  # Reduced for speed
            else:
                logger.error("Username input field not found")
                return False, "Username input field not found"
            await page.fill('input[name="email"]', '')  # Email vacío
            await asyncio.sleep(0.05)  # Reduced for speed
            await page.fill('input[name="name"]', '')  # Nombre vacío
            await asyncio.sleep(0.05)  # Reduced for speed
            await page.fill('input[name="surname"]', '')  # Apellido vacío
            await asyncio.sleep(0.05)  # Reduced for speed

            # Use type() for password fields to trigger proper state updates
            password_input = await page.query_selector('input[name="password"]')
            if password_input:
                await password_input.click()
                await asyncio.sleep(0.05)  # Reduced for speed
                await password_input.fill('')
                await asyncio.sleep(0.05)  # Reduced for speed
                await password_input.type(password, delay=50)  # Faster typing
                logger.info(f"Password field filled")
                await asyncio.sleep(0.4)  # Reduced from 0.7s for speed

            confirm_password_input = await page.query_selector('input[name="confirmPassword"]')
            if confirm_password_input:
                await confirm_password_input.click()
                await asyncio.sleep(0.05)  # Reduced for speed
                await confirm_password_input.fill('')
                await asyncio.sleep(0.05)  # Reduced for speed
                await confirm_password_input.type(password, delay=50)  # Faster typing
                logger.info(f"Confirm password field filled")
                await asyncio.sleep(0.4)  # Reduced from 0.7s for speed

            # Remove role field from form if it exists (let backend assign it automatically)
            await page.evaluate("""
                const form = document.querySelector('form');
                if (form) {
                    const roleInput = form.querySelector('input[name="role"]');
                    if (roleInput) {
                        roleInput.remove();
                    }
                }
            """)
            await asyncio.sleep(0.05)  # Reduced for speed
            
            # Debug: capture form data before submission
            form_data = await page.evaluate("""
                () => {
                    const form = document.querySelector('form');
                    if (!form) return null;
                    const formData = new FormData(form);
                    const data = {};
                    for (let [key, value] of formData.entries()) {
                        data[key] = value;
                    }
                    return data;
                }
            """)
            logger.info(f"Form data before submission: {form_data}")

            # Submit the form
            await page.click('button[type="submit"]')
            logger.info("User creation form submitted, waiting for confirmation modal...")

            # Wait for confirmation modal to appear and be ready
            await asyncio.sleep(0.4)  # Reduced from 0.7s for speed

            # Click the confirmation button in the modal
            try:
                # Wait for modal to appear
                modal_button = await page.wait_for_selector(
                    'button:has-text("Crear jugador")',
                    timeout=6000,  # +1 second (was 5000)
                    state='visible'
                )
                if modal_button:
                    logger.info("Confirmation modal found, clicking 'Crear jugador' button...")
                    # Wait a bit to ensure modal is fully interactive
                    await asyncio.sleep(0.2)  # Reduced for speed
                    await modal_button.click()
                    logger.info("Confirmation button clicked, waiting for backend processing...")
                    # Wait for backend to process the request
                    await asyncio.sleep(0.6)  # Reduced from 1.0s for speed
                else:
                    logger.warning("Confirmation modal button not found")
            except Exception as e:
                logger.error(f"Error clicking confirmation modal button: {e}")
                return False, f"Failed to confirm user creation: {str(e)}"

            # Wait for and check toast notifications with extended timeout
            success = False
            error_message = None
            
            try:
                # Wait longer for notifications to appear (some sites take time)
                logger.info("Waiting for toast notification...")
                notification = await page.wait_for_selector(
                    '.notification__text',
                    timeout=10000,  # Wait up to 10 seconds for notification
                    state='visible'
                )
                
                if notification:
                    logger.info("Toast notification found, checking text...")

                    # Get the notification message text
                    notification_text = await notification.text_content()
                    logger.info(f"Toast notification text: '{notification_text}'")

                    if notification_text:
                        notification_lower = notification_text.lower().strip()

                        # Check for success indicators (including Spanish "Éxito")
                        if any(word in notification_lower for word in ['éxito', 'success', 'creado', 'created', 'successful', 'exitoso']):
                            logger.info(f"✅ User {username} created successfully - confirmed by toast")
                            success = True
                        # Check for error indicators
                        elif any(word in notification_lower for word in ['error', 'failed', 'existe', 'exists', 'invalid', 'inválido', 'fallo']):
                            error_message = f"User creation failed: {notification_text}"
                            logger.error(error_message)
                            success = False
                        else:
                            logger.warning(f"Ambiguous notification: {notification_text}")
                            success = False
                    else:
                        logger.warning("Toast notification found but empty text")
                        success = False
                else:
                    logger.warning("No toast notification found")
                    success = False
                    error_message = "No confirmation notification received"
                    
            except Exception as e:
                logger.error(f"Error waiting for toast notification: {e}")
                error_message = f"Failed to get confirmation: {str(e)}"
                success = False
            
            # If we have a definitive result from toast, use it
            if success:
                logger.info(f"User {username} creation confirmed by toast notification")
                return True, "User created successfully"
            elif error_message:
                logger.error(f"User {username} creation failed: {error_message}")
                return False, error_message
            
            # Fallback check: if no toast found, check form state and page behavior
            logger.info("No definitive toast found, performing fallback checks...")
            
            # Wait a bit more for page to settle
            await asyncio.sleep(0.3)  # Reduced from 0.5s for speed
            
            # Check if form was cleared (common success indicator)
            try:
                username_value = await page.get_attribute('input[name="username"]', 'value')
                if not username_value or username_value.strip() == "":
                    logger.info("Form cleared - likely successful user creation")
                    return True, "User created successfully (form cleared)"
                else:
                    logger.error("Form still contains data - likely failed user creation")
                    return False, "User creation failed: Form validation error"
            except Exception as e:
                logger.error(f"Error checking form state: {e}")
                return False, f"User creation status unclear: {str(e)}"
            
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

async def assign_balance(username, amount, bonus_percentage=None):
    """Assign balance to a user on the platform

    Args:
        username: The username to assign balance to
        amount: The amount to deposit
        bonus_percentage: Optional bonus percentage (e.g., 50 for 50% bonus)
    """
    try:
        context = await get_browser_context()
        page = await context.new_page()
        
        try:
            # Login to the platform (will skip if already logged in)
            login_success, page = await login_to_platform(page)
            if not login_success:
                error_msg = "Failed to login to the platform"
                logger.error(error_msg)
                return False, error_msg
            
            # Navigate with minimal waiting
            await page.goto(BALANCE_URL, wait_until="domcontentloaded")
            
            # Wait for page to be ready
            await asyncio.sleep(0.2)  # Reduced from 0.3s for speed

            # Search for the user
            search_input = await page.query_selector('input[placeholder="Buscar Usuario"]')
            if not search_input:
                error_msg = "Search input not found on balance page"
                logger.error(error_msg)
                return False, error_msg

            logger.info(f"Searching for user: {username}")
            await page.fill('input[placeholder="Buscar Usuario"]', username)
            
            # Wait for search results
            await asyncio.sleep(0.3)  # Reduced from 0.5s for speed
            
            # Find user row with parallel processing - try twice if user not found initially
            user_found = False
            search_attempts = 0
            max_search_attempts = 2
            
            while not user_found and search_attempts < max_search_attempts:
                search_attempts += 1
                logger.info(f"Search attempt {search_attempts} for user: {username}")

                user_rows = await page.query_selector_all('.adm-bets-table-row-user')
                
                if not user_rows:
                    logger.warning(f"No users found in search results for: {username} (attempt {search_attempts})")
                    
                    # If no users found and this is the first attempt, try clicking search button
                    if search_attempts == 1:
                        logger.info("Attempting to click search button to refresh results")
                        try:
                            # Look for the search button (Aplicar filtro)
                            search_button = await page.query_selector('button[type="submit"].button.button_sizable_default.button_colors_default')
                            if search_button:
                                logger.info("Found search button, clicking it")
                                await search_button.click()
                                
                                # Wait for spinner to appear and then disappear
                                logger.info("Waiting for spinner loader to appear and disappear")
                                await asyncio.sleep(1.5)  # Reduced from 3.0s for speed
                                
                            else:
                                logger.warning("Search button not found")
                                await asyncio.sleep(1.0)  # +1 second (was 1.0)
                                
                        except Exception as e:
                            logger.error(f"Error clicking search button: {e}")
                            await asyncio.sleep(1.0)  # +1 second (was 1.0)
                    
                    # Continue to next attempt or exit if max attempts reached
                    if search_attempts >= max_search_attempts:
                        error_msg = f"No users found in search results for: {username} after {max_search_attempts} attempts"
                        logger.error(error_msg)
                        return False, error_msg
                    continue
                
                # Check each user row for matching username
                for user_row in user_rows:
                    username_element = await user_row.query_selector('.adm-bets-table-row-user__td-data-user span')
                    if username_element:
                        row_username = await username_element.text_content()
                        if row_username and row_username.strip() == username:
                            # Find the "Depositar" button
                            deposit_button = await user_row.query_selector('a.button.button_sizable_default.button_colors_default')
                            if deposit_button:
                                # Verify it's the deposit button by checking text
                                button_text = await deposit_button.text_content()
                                if button_text and 'Depositar' in button_text:
                                    logger.info(f"Found user {username}, clicking Depositar button")
                                    await deposit_button.click()
                                    user_found = True
                                    break
                
                # If user still not found after checking all rows, continue to next attempt
                if not user_found:
                    logger.warning(f"User {username} not found in current results (attempt {search_attempts})")
                    
                    # If this is not the last attempt, try clicking search button again
                    if search_attempts < max_search_attempts:
                        logger.info("Trying search button click for next attempt")
                        try:
                            search_button = await page.query_selector('button[type="submit"].button.button_sizable_default.button_colors_default')
                            if search_button:
                                await search_button.click()
                                await asyncio.sleep(1.0)  # +1 second (was 1.0)
                        except Exception as e:
                            logger.warning(f"Error in additional search button click: {e}")
            
            if not user_found:
                error_msg = f"User {username} not found in search results after {max_search_attempts} attempts"
                logger.error(error_msg)
                return False, error_msg
            
            # Wait for deposit form to load
            await asyncio.sleep(0.3)  # Reduced from 0.5s for speed
            
            # Check if deposit form loaded
            amount_input = await page.query_selector('input[placeholder="Monto"]')
            submit_button = await page.query_selector('button[type="submit"]')

            if not amount_input or not submit_button:
                error_msg = "Deposit form elements not found"
                logger.error(error_msg)
                return False, error_msg

            logger.info(f"Filling amount: {amount}")
            
            # Enable request/response interception for balance API
            async def log_balance_request_response(route, request):
                response = await route.fetch()
                
                # Log balance API request/response
                if '/api/' in request.url and request.method == 'POST':
                    logger.info(f"Balance POST Request URL: {request.url}")
                    logger.info(f"Balance POST Request Headers: {request.headers}")
                    try:
                        post_data = request.post_data
                        logger.info(f"Balance POST Request Payload: {post_data}")
                    except:
                        logger.warning("Could not capture balance POST data")
                    
                    # Log response details
                    logger.info(f"Balance Response Status: {response.status}")
                    logger.info(f"Balance Response Headers: {response.headers}")
                    try:
                        response_body = await response.text()
                        logger.info(f"Balance Response Body: {response_body}")
                    except Exception as e:
                        logger.warning(f"Could not capture balance response body: {e}")
                
                await route.fulfill(response=response)

            await page.route('**/*', log_balance_request_response)
            
            # Fill amount field
            await page.fill('input[placeholder="Monto"]', '')  # Clear first
            await page.fill('input[placeholder="Monto"]', str(amount))
            await asyncio.sleep(0.05)  # Reduced from 0.1s for speed

            # Handle bonus if provided
            if bonus_percentage is not None:
                logger.info(f"Activating bonus: {bonus_percentage}%")

                # Find the bonus switcher (custom div element, not a standard checkbox)
                bonus_switch = await page.query_selector('div.switcher')

                if bonus_switch:
                    # Check if already active by looking for 'switcher_active' class
                    class_attr = await bonus_switch.get_attribute('class')
                    is_active = 'switcher_active' in class_attr if class_attr else False

                    if not is_active:
                        logger.info("Bonus switch is inactive, activating it...")
                        await bonus_switch.click()
                        logger.info("Bonus switch activated")
                        await asyncio.sleep(0.1)
                    else:
                        logger.info("Bonus switch already active")

                    # Find and fill the bonus percentage field
                    # Use specific selector to avoid confusion with the main amount field
                    bonus_input = await page.query_selector('input[placeholder="Por ciento %"]')
                    if not bonus_input:
                        # Try using the bonus-specific class
                        bonus_input = await page.query_selector('input.input_bonus')
                    if not bonus_input:
                        # Try combining name with class to be specific
                        bonus_input = await page.query_selector('input[name="amount"].input_bonus')

                    if bonus_input:
                        await bonus_input.fill('')  # Clear first
                        await bonus_input.fill(str(bonus_percentage))
                        logger.info(f"Bonus percentage filled: {bonus_percentage}%")
                        await asyncio.sleep(0.05)
                    else:
                        logger.warning("Bonus input field not found (tried placeholder 'Por ciento %' and class 'input_bonus')")
                else:
                    logger.warning("Bonus switch not found (looking for div.switcher)")

            # Submit the deposit form
            await page.click('button[type="submit"]')
            logger.info("Balance assignment form submitted, waiting for confirmation...")
            
            # Wait for and check toast notifications
            success = False
            error_message = None
            
            try:
                # Wait for notifications to appear
                logger.info("Waiting for balance assignment toast notification...")
                notification = await page.wait_for_selector(
                    '.notification__text',
                    timeout=10000,  # Wait up to 10 seconds
                    state='visible'
                )
                
                if notification:
                    logger.info("Toast notification found for balance assignment")

                    # Get notification text
                    notification_text = await notification.text_content()
                    logger.info(f"Balance assignment toast text: '{notification_text}'")

                    if notification_text:
                        notification_lower = notification_text.lower().strip()

                        # Check for success indicators (Spanish and English)
                        if any(word in notification_lower for word in ['éxito', 'success', 'agregado', 'added', 'depositado', 'deposited', 'acreditado', 'credited', 'completado', 'completed', 'exitoso']):
                            logger.info(f"✅ Balance assignment successful: {notification_text}")
                            success = True
                        # Check for error indicators
                        elif any(word in notification_lower for word in ['error', 'failed', 'insuficiente', 'insufficient', 'invalid', 'inválido', 'fallo']):
                            error_message = f"Balance assignment failed: {notification_text}"
                            logger.error(error_message)
                            success = False
                        else:
                            error_message = f"Ambiguous balance notification: {notification_text}"
                            logger.warning(error_message)
                            success = False
                    else:
                        logger.warning("Balance assignment toast found but empty text")
                        error_message = "Balance notification appeared but no message text"
                        success = False
                else:
                    logger.warning("No balance assignment toast notification found")
                    error_message = "No balance assignment confirmation received"
                    success = False
                    
            except Exception as e:
                logger.error(f"Error waiting for balance assignment toast: {e}")
                error_message = f"Failed to get balance assignment confirmation: {str(e)}"
                success = False
            
            # Return definitive result
            if success:
                logger.info(f"Balance assignment to {username} confirmed by toast")
                return True, "Balance assigned successfully"
            else:
                logger.error(f"Balance assignment to {username} failed: {error_message}")
                return False, error_message or "Balance assignment failed - no confirmation received"
            
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