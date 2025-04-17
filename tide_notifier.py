import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from pushbullet import Pushbullet

# Check if .env was loaded correctly
access_token = os.getenv('PUSHBULLET_ACCESS_TOKEN')
if access_token is None:
    print("Error: PUSHBULLET_ACCESS_TOKEN not found in .env file")
    exit()

# Launch browser (headless if you prefer)
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # Comment this out to see the browser
driver = webdriver.Chrome(options=options)

# Navigate to page
driver.get("http://tidepredictions.pla.co.uk/")

# Wait for the tide table to populate (adjust selector & timeout as needed)
WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CSS_SELECTOR, ".TideNow1_tbody tr"))
)

# Get rendered page source
soup = BeautifulSoup(driver.page_source, 'html.parser')
driver.quit()

# Now parse the tbody as usual
tbody = soup.find('tbody', class_='TideNow1_tbody')
rows = tbody.find_all('tr')
row_data = []
for row in rows:
    cells = [td.get_text(strip=True) for td in row.find_all('td')]
    if cells and cells[0] == "London Bridge":
        row_data = [cells]  # First row
    elif row_data:
        row_data.append(cells)  # Second row (heights)
        break  # Done, no need to go further

# Check if London Bridge data was found
if not row_data:
    print("Error: London Bridge data not found.")
    exit()

tide_info = {
    "station": "London Bridge",
    "predicted": row_data[0][1],
    "next_high_time": row_data[0][2],
    "next_low_time": row_data[0][3],
    "high_height": row_data[1][0],
    "low_height": row_data[1][1],
}

# Push notification with tide data
pb = Pushbullet(access_token)

message = f"""🌊 London Bridge Tide Update:
Predicted: {tide_info['predicted']}
High Tide: {tide_info['next_high_time']} ({tide_info['high_height']})
Low Tide: {tide_info['next_low_time']} ({tide_info['low_height']})
"""

push = pb.push_note("Tide Times - London Bridge", message)
