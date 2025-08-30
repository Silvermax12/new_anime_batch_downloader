import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from browser import create_stealth_driver, guarded_click, cleanup_browser_data


def scrape_download_links(anime_session, episode_session, max_retries=2):
    """Scrape download links with retry logic and better error handling"""
    url = f"https://animepahe.ru/play/{anime_session}/{episode_session}"
    
    for attempt in range(max_retries):
        driver = None
        try:
            print(f"🌐 Scraping attempt {attempt + 1}/{max_retries} for {url}")
            driver = create_stealth_driver(headless=True)
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Look for download button
            download_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "downloadMenu"))
            )
            
            # Click download button
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_button)
                download_button.click()
            except Exception as e:
                print(f"⚠️ Direct click failed, trying guarded click: {e}")
                guarded_click(driver, download_button, max_retries=3)
            
            # Wait for dropdown to appear
            dropdown = WebDriverWait(driver, 20).until(
                EC.visibility_of_element_located((By.ID, "pickDownload"))
            )
            
            # Extract download links
            anchors = dropdown.find_elements(By.TAG_NAME, "a")
            links = {}
            
            for a in anchors:
                href = a.get_attribute("href")
                text = a.text.strip()
                match = re.search(r"(\d{3,4})p", text)
                if href and match:
                    quality = match.group(1)
                    if "eng" in text.lower():
                        lang = "eng"
                    elif "chi" in text.lower():
                        lang = "chi"
                    else:
                        lang = "jpn"
                    links[f"{quality}_{lang}"] = href
            
            if links:
                print(f"✅ Successfully scraped {len(links)} download links")
                return links
            else:
                print(f"⚠️ No download links found on attempt {attempt + 1}")
                
        except TimeoutException as ex:
            print(f"⚠️ Timeout on attempt {attempt + 1}: {ex}")
            if attempt == max_retries - 1:
                raise Exception(f"Page load timeout after {max_retries} attempts. The episode may not be available.")
                
        except Exception as ex:
            print(f"⚠️ Error on attempt {attempt + 1}: {ex}")
            if attempt == max_retries - 1:
                raise Exception(f"Failed to scrape download links: {str(ex)}")
                
        finally:
            if driver:
                try:
                    cleanup_browser_data(driver)  # Clean up temp directory first
                    driver.quit()
                except Exception as e:
                    print(f"⚠️ Error closing driver: {e}")
        
        # Wait before retry
        if attempt < max_retries - 1:
            print(f"⏳ Waiting before retry...")
            time.sleep(2 ** attempt + 1)  # Exponential backoff + 1 second minimum
    
    return {}


