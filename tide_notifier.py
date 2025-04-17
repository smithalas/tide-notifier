import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pushbullet import Pushbullet

# Load environment variables
load_dotenv()

from pushbullet import Pushbullet

# Get Pushbullet token and station name from environment variables
access_token = os.environ.get('PUSHBULLET_ACCESS_TOKEN')
station_name = os.environ.get('STATION_NAME')

# Error handling for missing environment variables
if access_token is None:
    print("Error: PUSHBULLET_ACCESS_TOKEN not found in environment")
    exit()

if station_name is None:
    print("Error: STATION_NAME not found in environment")
    exit()

# Set up WebDriver (headless mode)
options = webdriver.ChromeOptions()
options.add_argument("--headless")
driver = webdriver.Chrome(options=options)

# Fetch tide prediction page
try:
    driver.get("http://tidepredictions.pla.co.uk/")

    # Wait for page elements to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".TideNow1_tbody tr"))
    )

    # Parse page with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')

finally:
    # Ensure the driver is closed even if an error occurs
    driver.quit()

# Find the tide data in the parsed HTML
tbody = soup.find('tbody', class_='TideNow1_tbody')
rows = tbody.find_all('tr')
row_data = []

# Extract the data for the station we're interested in
for row in rows:
    cells = [td.get_text(strip=True) for td in row.find_all('td')]
    if cells and cells[0] == station_name:
        row_data.append(cells)  # First row (predicted tide times)
    elif row_data:
        row_data.append(cells)  # Second row (heights)
        break

# Error handling if the data is not found
if not row_data:
    print(f"Error: {station_name} data not found.")
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
