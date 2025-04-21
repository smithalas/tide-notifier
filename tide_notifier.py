import os
import logging
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pushbullet import Pushbullet

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)

# Get Pushbullet token and station name from environment variables
load_dotenv()
access_token = os.environ.get('PUSHBULLET_ACCESS_TOKEN')
station_name = os.environ.get('STATION_NAME', '').strip()  # Stripping to avoid trailing spaces

# Error handling for missing environment variables
if access_token is None:
    logging.error("PUSHBULLET_ACCESS_TOKEN not found in environment")
    exit()

if not station_name:
    logging.error("STATION_NAME not found in environment")
    exit()

# Set up WebDriver (headless mode with extra options for CI environments)
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920x1080")  # Ensure viewport size is large enough to load content
options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

# Only set the binary location if running in CI (GitHub Actions)
if os.environ.get("CI") == "true":  # CI environment variable is set to 'true' in GitHub Actions
    logging.info("Running in CI (GitHub Actions), setting Chrome binary location...")
    options.binary_location = "/usr/bin/google-chrome-stable"

# Initialize WebDriver
driver = webdriver.Chrome(options=options)

# Fetch tide prediction page
from selenium.common.exceptions import TimeoutException  # Add this at the top

# Fetch tide prediction page
try:
    logging.info(f"Fetching tide data for {station_name}...")
    driver.get("http://tidepredictions.pla.co.uk/")

    # Wait for page elements to load
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".TideNow1_tbody tr"))
        )
    except TimeoutException:
        logging.error("Timeout waiting for tide table to load.")
        driver.save_screenshot("tide_debug_timeout.png")
        with open("page_source_timeout.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.quit()
        exit()

    # Parse page with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Log first 1000 characters of the fetched page for debugging
    logging.debug("Fetched page source:\n" + soup.prettify()[:1000])

finally:
    with open("page_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    driver.save_screenshot("tide_debug.png")
    driver.quit()

# Find the tide data in the parsed HTML
tbody = soup.find('tbody', class_='TideNow1_tbody')
rows = tbody.find_all('tr')
row_data = []

# Extract the data for the station we're interested in
for row in rows:
    cells = [td.get_text(strip=True) for td in row.find_all('td')]
    logging.debug(f"Row data: {cells}")
    if cells and cells[0] == station_name:
        row_data.append(cells)  # First row (predicted tide times)
    elif row_data:
        row_data.append(cells)  # Second row (heights)
        break

# Error handling if the data is not found
if not row_data:
    logging.error(f"Error: No data found for {station_name}.")
    exit()

# Prepare the tide information for the notification
tide_info = {
    "station": station_name,
    "predicted": row_data[0][1],
    "next_high_time": row_data[0][2],
    "next_low_time": row_data[0][3],
    "high_height": row_data[1][0],
    "low_height": row_data[1][1],
}

# Push notification with tide data
pb = Pushbullet(access_token)

message = f"""🌊 {station_name} Tide Update:
Predicted: {tide_info['predicted']}
High Tide: {tide_info['next_high_time']} ({tide_info['high_height']})
Low Tide: {tide_info['next_low_time']} ({tide_info['low_height']})
"""

# Send the push notification
push = pb.push_note(f"Tide Times - {station_name}", message)

# Log the message being sent
logging.info(f"Push notification sent: {message}")