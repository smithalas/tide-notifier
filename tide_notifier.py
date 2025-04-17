import os
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pushbullet import Pushbullet

# ------------------------------
# Logging Setup
# ------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
)

# ------------------------------
# Load Environment Variables
# ------------------------------
access_token = os.environ.get('PUSHBULLET_ACCESS_TOKEN')
station_name = os.environ.get('STATION_NAME')

# ------------------------------
# Environment Variable Checks
# ------------------------------
if access_token is None:
    logging.error("PUSHBULLET_ACCESS_TOKEN not found in environment")
    exit()

if station_name is None:
    logging.error("STATION_NAME not found in environment")
    exit()

logging.info(f"Using station: {station_name}")

# ------------------------------
# Set up WebDriver
# ------------------------------
options = webdriver.ChromeOptions()
options.add_argument("--headless")
driver = webdriver.Chrome(options=options)

# ------------------------------
# Fetch Tide Prediction Page
# ------------------------------
try:
    driver.get("http://tidepredictions.pla.co.uk/")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".TideNow1_tbody tr"))
    )
    soup = BeautifulSoup(driver.page_source, 'html.parser')
finally:
    driver.quit()

# ------------------------------
# Extract Tide Data
# ------------------------------
tbody = soup.find('tbody', class_='TideNow1_tbody')
rows = tbody.find_all('tr')
row_data = []

logging.debug("Available stations on the page:")
for row in rows:
    cells = [td.get_text(strip=True) for td in row.find_all('td')]
    if cells:
        logging.debug(f" - {cells[0]}")
    if cells and cells[0].strip().lower() == station_name.strip().lower():
        logging.info(f"Found matching station row: {cells}")
        row_data.append(cells)
    elif row_data:
        row_data.append(cells)
        break

if not row_data or len(row_data) < 2:
    logging.error(f"{station_name} data not found or incomplete.")
    exit()

logging.debug(f"Collected row data: {row_data}")

# ------------------------------
# Prepare Notification
# ------------------------------
tide_info = {
    "station": station_name,
    "predicted": row_data[0][1],
    "next_high_time": row_data[0][2],
    "next_low_time": row_data[0][3],
    "high_height": row_data[1][0],
    "low_height": row_data[1][1],
}

pb = Pushbullet(access_token)

message = f"""🌊 {station_name} Tide Update:
Predicted: {tide_info['predicted']}
High Tide: {tide_info['next_high_time']} ({tide_info['high_height']})
Low Tide: {tide_info['next_low_time']} ({tide_info['low_height']})
"""

logging.info("Sending push notification...")
push = pb.push_note(f"Tide Times - {station_name}", message)
logging.info("Notification sent successfully.")
