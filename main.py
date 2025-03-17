import os
import time
import shutil
import traceback
import logging
from datetime import datetime, timedelta
import zipfile

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException

# ---------------------------------------------------------------------------
# Configuration for local downloads and dynamic folder creation
base_local_dir = os.path.join(os.getcwd(), "downloads")
current_month_folder = datetime.now().strftime("%B %Y")
base_download_dir = os.path.join(base_local_dir, current_month_folder)
os.makedirs(base_download_dir, exist_ok=True)

# Setup logging: logs will be written to a file in the download directory.
log_filename = os.path.join(base_download_dir, f"Tracking Networks Downloaded and Skipped [{datetime.now().strftime('%Y-%m-%d')}].txt")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=log_filename,
    filemode='w'
)
logger = logging.getLogger()
# Also output logs to console.
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

logger.info("Starting script...")

# ---------------------------------------------------------------------------
# Configure Chrome options for automatic downloading in headless mode
chrome_options = Options()
chrome_options.add_argument("--headless")               # Run in headless mode
chrome_options.add_argument("--disable-gpu")            # Disable GPU usage
chrome_options.add_argument("--no-sandbox")             # Bypass OS security model
chrome_options.add_argument("--disable-dev-shm-usage")    # Overcome limited resource problems
chrome_options.add_argument("--start-maximized")        # Optional: start maximized

chrome_prefs = {
    "download.default_directory": base_download_dir,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
}
chrome_options.add_experimental_option("prefs", chrome_prefs)

# ---------------------------------------------------------------------------
# Function to initialize the WebDriver
def init_driver():
    global driver, wait
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 30)

# Initialize driver
init_driver()

def reinitialize_driver():
    """Reopens Chrome, logs in again, and navigates back to 'Scheduling Results By Path'."""
    global driver, wait
    logger.info("⚠️ Chrome browser closed unexpectedly. Reinitializing driver...")
    try:
        driver.quit()
    except Exception:
        pass
    init_driver()
    try:
        driver.get("https://gms.gasmalaysia.com/pltgtm/cmd.openseal?openSEAL_ck=ViewHome")
        website_username = os.environ.get("WEBSITE_USERNAME")
        website_password = os.environ.get("WEBSITE_PASSWORD")
        username_field = wait.until(EC.visibility_of_element_located((By.ID, "UserCtrl")))
        password_field = wait.until(EC.visibility_of_element_located((By.ID, "PwdCtrl")))
        username_field.send_keys(website_username)
        time.sleep(2)
        password_field.send_keys(website_password)
        time.sleep(2)
        login_button = wait.until(EC.element_to_be_clickable((By.NAME, "btnLogin")))
        login_button.click()
        time.sleep(2)
        scheduling_tab = wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Scheduling")))
        ActionChains(driver).move_to_element(scheduling_tab).click().perform()
        time.sleep(2)
        scheduling_results_by_path = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Scheduling Results By Path")))
        scheduling_results_by_path.click()
        logger.info("✅ Reinitialized and navigated back to Allocation Results By Path")
    except Exception as e:
        logger.info(f"❌ Failed to reinitialize driver: {e}")

def wait_for_loading():
    """Waits for the loading spinner (`k-loading-image`) to disappear."""
    logger.info("⏳ Waiting for page to load...")
    while True:
        try:
            loading_elements = driver.find_elements(By.CLASS_NAME, "k-loading-image")
            if not loading_elements:
                logger.info("✅ Loading finished! Proceeding to export.")
                return
        except Exception:
            pass
        time.sleep(1)

def wait_for_download(old_files):
    """Waits for the Excel file to appear in the download folder and returns its filename."""
    timeout = 120
    end_time = time.time() + timeout
    while time.time() < end_time:
        files = [f for f in os.listdir(base_download_dir) if f.endswith(".xlsx")]
        new_files = list(set(files) - set(old_files))
        if new_files:
            downloaded_file = os.path.join(base_download_dir, new_files[0])
            logger.info(f"✅ Detected downloaded file: {downloaded_file}")
            return downloaded_file
        time.sleep(2)
    logger.info("❌ No downloaded file detected.")
    return None

def format_network_name(network_name):
    """Converts 'C-Bandar Baru Nilai' to 'Scheduling Bandar Baru Nilai.xlsx'."""
    if "-" in network_name:
        return f"Scheduling {network_name.split('-', 1)[1].strip()}.xlsx"
    return f"Scheduling {network_name.strip()}.xlsx"

def select_dropdown(dropdown_index, option_text):
    """Selects an option from a dropdown list using index (1: Network, 2: Shipper, 3: Unit)."""
    for attempt in range(3):
        try:
            dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, f"(//span[@class='k-input'])[{dropdown_index}]")))
            dropdown.click()
            time.sleep(1)
            option = wait.until(EC.presence_of_element_located((By.XPATH, f"//li[contains(text(), '{option_text}')]")))
            option.click()
            logger.info(f"✅ Successfully selected: {option_text}")
            return
        except Exception:
            logger.info(f"⚠️ Attempt {attempt + 1}: Failed to select '{option_text}', retrying...")
            time.sleep(2)
    logger.info(f"❌ Failed to select '{option_text}' after 3 attempts.")

def set_date_input(date_str, start=True):
    """
    Sets the date in the datepicker input field directly.
    
    Parameters:
        date_str (str): The date string to input (e.g., "01/02/2025").
        start (bool): True to set the start date, False for the end date.
    """
    try:
        date_input_id = "startdatepicker" if start else "enddatepicker"
        date_input = driver.find_element(By.ID, date_input_id)
        date_input.clear()
        date_input.send_keys(date_str)
        logger.info(f"✅ Set {'start' if start else 'end'} date to {date_str}")
    except Exception as e:
        logger.error(f"❌ Failed to set {'start' if start else 'end'} date: {e}")

def click_export_button():
    """Clicks the export button and returns True if successful, otherwise False."""
    try:
        export_button = wait.until(EC.element_to_be_clickable((By.ID, "delivery-export")))
        driver.execute_script("arguments[0].click();", export_button)
        logger.info("✅ Export button clicked via standard wait.")
        return True
    except Exception as e:
        logger.info(f"⚠️ Export button not found or clickable: {e}. Skipping this network.")
        return False

# ---------------------------------------------------------------------------
# Calculate dynamic dates:
# - Start date: always the 1st day of the current month.
# - End date: always the next day from today.
current_date = datetime.now()
start_date_str = f"01/{current_date.month:02d}/{current_date.year}"
end_date = current_date + timedelta(days=1)
end_date_str = f"{end_date.day:02d}/{end_date.month:02d}/{end_date.year}"
logger.info(f"Dynamic date range - Start: {start_date_str}, End: {end_date_str}")

# Lists to track summary
downloaded_networks = []
skipped_networks = []

# ---------------------------------------------------------------------------
# Retrieve network names (once, to avoid reinitialization issues)
try:
    driver.get("https://gms.gasmalaysia.com/pltgtm/cmd.openseal?openSEAL_ck=ViewHome")
    website_username = os.environ.get("WEBSITE_USERNAME")
    website_password = os.environ.get("WEBSITE_PASSWORD")
    username_field = wait.until(EC.visibility_of_element_located((By.ID, "UserCtrl")))
    password_field = wait.until(EC.visibility_of_element_located((By.ID, "PwdCtrl")))
    username_field.send_keys(website_username)
    time.sleep(2)
    password_field.send_keys(website_password)
    time.sleep(2)
    login_button = wait.until(EC.element_to_be_clickable((By.NAME, "btnLogin")))
    login_button.click()
    time.sleep(2)
    scheduling_tab = wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Scheduling")))
    ActionChains(driver).move_to_element(scheduling_tab).click().perform()
    time.sleep(2)
    scheduling_results_by_path = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Scheduling Results By Path")))
    scheduling_results_by_path.click()
    logger.info("✅ Successfully navigated to Allocation Results By Path")
    network_dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, "(//span[@class='k-input'])[1]")))
    network_dropdown.click()
    time.sleep(2)
    network_options = driver.find_elements(By.XPATH, "//ul[@id='NetworkCode_listbox']/li")
    network_names = [option.text for option in network_options]
    network_dropdown.click()  # Close the dropdown
    logger.info(f"🔍 Found {len(network_names)} networks: {network_names}")
except Exception as e:
    logger.info(traceback.format_exc())
    driver.quit()
    raise e

# ---------------------------------------------------------------------------
# Process each network with retry logic on WebDriverException
for network in network_names:
    network_retries = 0
    max_network_retries = 3
    processed = False
    while not processed and network_retries < max_network_retries:
        try:
            logger.info(f"Processing network: {network} (Attempt {network_retries+1}/{max_network_retries})")
            old_files = os.listdir(base_download_dir)
            select_dropdown(1, network)
            select_dropdown(2, "All")
            select_dropdown(3, "GJ")
            # Set dynamic dates
            set_date_input(start_date_str, start=True)
            set_date_input(end_date_str, start=False)
            search_button = wait.until(EC.element_to_be_clickable((By.ID, "search")))
            search_button.click()
            wait_for_loading()
            if not click_export_button():
                logger.info(f"⚠️ Skipping network '{network}' due to no export button (no data available).")
                skipped_networks.append(network)
                processed = True
                break
            downloaded_file = wait_for_download(old_files)
            if downloaded_file:
                new_file_name = format_network_name(network)
                new_file_path = os.path.join(base_download_dir, new_file_name)
                shutil.move(downloaded_file, new_file_path)
                logger.info(f"✅ Renamed '{downloaded_file}' to '{new_file_path}'")
                downloaded_networks.append(network)
            else:
                logger.info(f"⚠️ No file downloaded for network '{network}'.")
                skipped_networks.append(network)
            time.sleep(5)
            processed = True
        except WebDriverException as wde:
            network_retries += 1
            logger.info(f"⚠️ WebDriverException encountered while processing network '{network}': {wde}. Reinitializing driver and retrying...")
            reinitialize_driver()
        except Exception as e:
            logger.info(f"❌ Exception encountered while processing network '{network}': {e}. Skipping network.")
            skipped_networks.append(network)
            processed = True

logger.info("\n=== Summary ===")
logger.info(f"Total networks processed: {len(network_names)}")
logger.info(f"Downloaded networks count: {len(downloaded_networks)}")
logger.info(f"Skipped networks count: {len(skipped_networks)}")
if downloaded_networks:
    logger.info("Networks with downloaded data:")
    for net in downloaded_networks:
        logger.info(f" - {net}")
else:
    logger.info("No networks were downloaded.")
if skipped_networks:
    logger.info("Networks skipped (no data or error):")
    for net in skipped_networks:
        logger.info(f" - {net}")
else:
    logger.info("All networks were downloaded successfully.")

driver.quit()
logger.info("Driver quit. Script finished.")

# ---------------------------------------------------------------------------
# New Section: Compress downloaded files for GitHub Actions Artifact

def compress_downloads_dir(directory, zip_filename):
    """Compresses all files in the given directory into a ZIP file."""
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                # Use relative path for the archive
                arcname = os.path.relpath(file_path, start=directory)
                zipf.write(file_path, arcname=arcname)
    logger.info(f"✅ Compressed files into {zip_filename}")

# Define the ZIP file path (created in base_local_dir)
zip_filename = os.path.join(base_local_dir, f"{current_month_folder}.zip")
compress_downloads_dir(base_download_dir, zip_filename)

logger.info("Artifact is ready. Use GitHub Actions 'upload-artifact' step to save the ZIP file.")
