# Web Browsing Automation using Selenium

## Overview
This project is a Python-based web browsing automation tool that uses Selenium WebDriver to automatically log in, navigate, and download scheduling results from a specified website. The automation is scheduled to run daily on GitHub Actions.

## Features
- Logs into the Gas Malaysia scheduling platform
- Selects dropdown options for different networks
- Sets date filters for monthly scheduling results
- Downloads and renames Excel files based on network names
- Logs all activities, including downloaded and skipped networks
- Runs in headless mode for cloud execution
- Automated execution via GitHub Actions on a daily schedule

## Prerequisites
Ensure you have the following installed on your local machine (if running locally):
- Python 3.x
- Google Chrome
- ChromeDriver

## Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/your-repository.git
   cd your-repository
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
To run the script locally, execute:
```bash
python main.py
```

## Configuration
- The script uses Selenium with Chrome in headless mode.
- Download directory is set to:
  ```
  C:\Users\umarul\OneDrive - Gas Malaysia Berhad\GMS Manual\Scheduling\2025\51. March 2025\Network (Monthly)
  ```
  However, this will be changed later due to requirement to run on cloud. This path will be changed to Microsoft SharePoint integration which the data from the automation    
  will be downloaded into
  
- Logging is enabled to track downloaded and skipped files.

## Cloud Execution (GitHub Actions)
The script is scheduled to run daily at 3:30 PM Kuala Lumpur time (7:30 AM UTC) using GitHub Actions.

### GitHub Actions Workflow
Located in `.github/workflows/selenium.yml`, this workflow:
1. Checks out the repository
2. Sets up Python
3. Installs dependencies
4. Runs the Selenium script

#### Schedule
The workflow is triggered:
- Daily at 3:30 PM KL time (7:30 AM UTC)
- Manually via GitHub Actions

### Manual Execution via GitHub Actions
To trigger a manual run:
1. Go to the GitHub repository
2. Navigate to `Actions`
3. Select the workflow `Run Selenium Script Daily`
4. Click `Run Workflow`

## Logging & Debugging
- All logs are saved in the download directory with the filename:
  ```
  Tracking Networks Downloaded and Skipped [YYYY-MM-DD].txt
  ```
- Logs include processed networks, downloaded files, and skipped files.

## Dependencies
Listed in `requirements.txt`:
```txt
selenium
webdriver-manager
```
