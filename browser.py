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
    
    # Create unique user data directory for this browser instance
    unique_id = str(uuid.uuid4())[:8]
    temp_dir = tempfile.gettempdir()
    user_data_dir = os.path.join(temp_dir, f"chrome_user_data_{unique_id}")
    
    print(f"🌐 Creating browser instance with unique user data dir: {user_data_dir}")
    
    if HAS_UC:
        opts = uc.ChromeOptions()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--window-size=1366,768")
        opts.add_argument(f"--user-data-dir={user_data_dir}")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--disable-plugins")
        opts.add_argument("--disable-images")  # Speed up loading
        try:
            driver = uc.Chrome(options=opts)
        except Exception as e:
            print(f"⚠️ UC Chrome failed: {e}, falling back to regular Chrome")
            # Fallback to regular Chrome if UC fails
            opts = Options()
            if headless:
                opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_argument("--window-size=1366,768")
            opts.add_argument(f"--user-data-dir={user_data_dir}")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--disable-extensions")
            opts.add_argument("--disable-plugins")
            opts.add_argument("--disable-images")
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option("useAutomationExtension", False)
            driver = webdriver.Chrome(options=opts)
    else:
        opts = Options()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--window-size=1366,768")
        opts.add_argument(f"--user-data-dir={user_data_dir}")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--disable-plugins")
        opts.add_argument("--disable-images")  # Speed up loading
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        driver = webdriver.Chrome(options=opts)
    
    try:
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    except Exception:
        pass
    
    # Store the user data directory path for cleanup
    driver._user_data_dir = user_data_dir
    
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
        if hasattr(driver, '_user_data_dir'):
            user_data_dir = driver._user_data_dir
            if os.path.exists(user_data_dir):
                import shutil
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


