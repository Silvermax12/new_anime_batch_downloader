import time
import random
import uuid
import tempfile
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
)
from config import AD_BLOCK_PATTERNS

try:
    import undetected_chromedriver as uc  # type: ignore
    HAS_UC = True
except Exception:
    HAS_UC = False


def create_stealth_driver(headless=True):
    """Create a stealth Chrome driver with unique user data directory to avoid conflicts"""

    # Create unique temp directory proactively to avoid collisions
    user_data_dir = tempfile.mkdtemp(prefix="chrome_user_data_")
    print(f"🌐 Creating browser instance with unique user data dir: {user_data_dir}")

    def _build_opts(base_opts):
        if headless:
            base_opts.add_argument("--headless=new")
        base_opts.add_argument("--no-sandbox")
        base_opts.add_argument("--disable-dev-shm-usage")
        base_opts.add_argument("--disable-blink-features=AutomationControlled")
        base_opts.add_argument("--window-size=1366,768")
        base_opts.add_argument(f"--user-data-dir={user_data_dir}")
        base_opts.add_argument("--disable-gpu")
        base_opts.add_argument("--disable-extensions")
        base_opts.add_argument("--disable-plugins")
        base_opts.add_argument("--blink-settings=imagesEnabled=false")  # Speed up loading
        return base_opts

    driver = None
    last_error = None

    # Try UC first if available
    if HAS_UC:
        try:
            opts = _build_opts(uc.ChromeOptions())
            driver = uc.Chrome(options=opts)
        except Exception as e:
            last_error = e
            print(f"⚠️ UC Chrome failed: {e}, falling back to regular Chrome")

    if driver is None:
        try:
            opts = _build_opts(Options())
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option("useAutomationExtension", False)
            driver = webdriver.Chrome(options=opts)
        except Exception as e:
            # Fallback: if user-data-dir causes issues, retry without it
            err_text = str(e).lower()
            if "user data directory is already in use" in err_text or "session not created" in err_text:
                print("🔁 Retrying Chrome launch without custom user-data-dir…")
                try:
                    opts = Options()
                    if headless:
                        opts.add_argument("--headless=new")
                    opts.add_argument("--no-sandbox")
                    opts.add_argument("--disable-dev-shm-usage")
                    opts.add_argument("--disable-blink-features=AutomationControlled")
                    opts.add_argument("--window-size=1366,768")
                    opts.add_argument("--disable-gpu")
                    opts.add_argument("--disable-extensions")
                    opts.add_argument("--disable-plugins")
                    opts.add_argument("--blink-settings=imagesEnabled=false")
                    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
                    opts.add_experimental_option("useAutomationExtension", False)
                    driver = webdriver.Chrome(options=opts)
                    # If we launched without a custom dir, mark it so cleanup is a no-op
                    user_data_dir = None
                except Exception as e2:
                    last_error = e2
            else:
                last_error = e

    if driver is None:
        # Cleanup created temp dir if driver failed to start
        try:
            if user_data_dir and os.path.exists(user_data_dir):
                import shutil
                shutil.rmtree(user_data_dir, ignore_errors=True)
        except Exception:
            pass
        raise last_error if last_error else RuntimeError("Failed to create Chrome driver")

    try:
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    except Exception:
        pass

    # Store the user data directory path for cleanup
    driver._user_data_dir = user_data_dir  # type: ignore[attr-defined]

    return driver


def set_adblock(driver, enabled: bool):
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": AD_BLOCK_PATTERNS if enabled else []})
    except Exception:
        pass


def close_new_tabs_and_return(driver, base_handle: str):
    try:
        handles = driver.window_handles
        for h in list(handles):
            if h != base_handle:
                try:
                    driver.switch_to.window(h)
                    driver.close()
                except Exception:
                    pass
        driver.switch_to.window(base_handle)
    except Exception:
        pass


def cleanup_browser_data(driver):
    """Clean up temporary user data directory after browser closes"""
    try:
        user_data_dir = getattr(driver, '_user_data_dir', None)
        if user_data_dir and os.path.exists(user_data_dir):
            import shutil
            # Ensure the browser has had a moment to release file locks
            try:
                time.sleep(0.2)
            except Exception:
                pass
            shutil.rmtree(user_data_dir, ignore_errors=True)
            print(f"🧹 Cleaned up browser data directory: {user_data_dir}")
    except Exception as e:
        print(f"⚠️ Failed to cleanup browser data: {e}")

def guarded_click(driver, element, max_retries: int = 3):
    base = driver.current_window_handle
    for _ in range(max_retries):
        pre_handles = set(driver.window_handles)
        try:
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.2)
            except Exception:
                pass
            try:
                ActionChains(driver).move_to_element(element).pause(0.1).click().perform()
            except Exception:
                element.click()
        except Exception:
            try:
                driver.execute_script("arguments[0].click();", element)
            except Exception:
                pass
        time.sleep(0.6 + random.uniform(0.1, 0.4))
        post_handles = set(driver.window_handles)
        if len(post_handles) > len(pre_handles):
            close_new_tabs_and_return(driver, base)
            time.sleep(0.4)
            continue
        return True
    return False


