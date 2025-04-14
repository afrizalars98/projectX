from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType
import time
import pandas as pd

def start_driver(headless=False):
    options = Options()
    if headless:
        options.add_argument("--headless=new")  # Use new headless mode
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Use WebDriverManager to automatically manage ChromeDriver
    driver = webdriver.Chrome(
        service=webdriver.chrome.service.Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()),
        options=options
    )
    return driver

def search_gmaps(driver, query):
    driver.get("https://www.google.com/maps")
    time.sleep(3)
    search_box = driver.find_element(By.ID, "searchboxinput")
    search_box.send_keys(query)
    search_box.send_keys(Keys.ENTER)
    time.sleep(5)  # Wait for results to load
    
    # Print the current URL to verify we're in the right place
    print(f"Current URL: {driver.current_url}")

def scroll_results(driver, max_scrolls=20):
    # Wait for the search results to load
    time.sleep(5)
    
    # Try multiple selectors to find the scrollable div
    try:
        scrollable_div = driver.find_element(By.CSS_SELECTOR, 'div[role="main"]')
    except:
        scrollable_div = driver.find_element(By.CSS_SELECTOR, 'div[aria-label="Results for padel court Jakarta"]')
    
    for _ in range(max_scrolls):
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
        time.sleep(2)  # Increased wait time for better loading

def extract_places(driver):
    # Wait for results to load
    time.sleep(5)
    
    # First try to find the main results container
    try:
        results_container = driver.find_element(By.CSS_SELECTOR, 'div[role="main"]')
        print("Found main results container")
    except:
        print("Could not find main results container")
        return []
    
    # Try different selectors to find place elements
    try:
        places = results_container.find_elements(By.CSS_SELECTOR, 'div[data-attrid]')
        print(f"Found {len(places)} place elements")
    except:
        print("Could not find place elements")
        return []
    
    results = []
    for place in places:
        try:
            # Try different selectors for name
            name = place.find_element(By.CSS_SELECTOR, 'h3').text
            print(f"Found place: {name}")
        except:
            name = "N/A"
            print("Could not find name")
        
        try:
            # Try different selectors for rating
            rating = place.find_element(By.CSS_SELECTOR, 'span[aria-label*="stars"]')
            rating = rating.get_attribute('aria-label').split()[0]
        except:
            rating = "N/A"
            print("Could not find rating")
        
        try:
            # Try different selectors for reviews
            reviews = place.find_element(By.CSS_SELECTOR, 'span[aria-label*="reviews"]')
            reviews = reviews.get_attribute('aria-label').split()[0]
        except:
            reviews = "N/A"
            print("Could not find reviews")
        
        try:
            # Try different selectors for address
            address = place.find_element(By.CSS_SELECTOR, 'div[data-attrid*="address"]')
            address = address.text
        except:
            address = "N/A"
            print("Could not find address")
        
        try:
            # Try different selectors for link
            link = place.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
        except:
            link = "N/A"
            print("Could not find link")
        
        results.append({
            "Name": name,
            "Rating": rating,
            "Reviews": reviews,
            "Address": address,
            "Link": link
        })
    
    print(f"Successfully extracted {len(results)} places")
    return results

def scrape_padel_courts(location="Jakarta", max_scrolls=15, headless=True):
    driver = start_driver(headless=headless)
    try:
        search_gmaps(driver, f"Padel {location}")
        scroll_results(driver, max_scrolls=max_scrolls)
        data = extract_places(driver)
        df = pd.DataFrame(data)
        df.to_csv("padel_courts.csv", index=False)
        print(f"Scraped {len(df)} padel courts.")
        return df
    finally:
        driver.quit()

# Run it
if __name__ == "__main__":
    scrape_padel_courts("Jakarta", max_scrolls=20, headless=False)