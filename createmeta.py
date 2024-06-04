import logging
# Configuring logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='.log',
    encoding='utf-8',
    format='%(asctime)s %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S',
    level=logging.DEBUG
)

import requests
import json
import os
from dotenv import load_dotenv

# https://developer.atlassian.com/server/jira/platform/jira-rest-api-example-discovering-meta-data-for-creating-issues-6291669/

# Load environment variables from .env file
load_dotenv()

# Get the absolute path of the script
script_dir = os.path.dirname(os.path.realpath(__file__))
# Concatenate the absolute path with the JSON file name
json_file_path = os.path.join(script_dir, "schema.json")

# Configuration
JIRA_URL = os.getenv("JIRA_URL")  # URL of the Jira instance
JIRA_EMAIL = os.getenv("JIRA_EMAIL")  # Email of the Jira user
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")  # Jira API token

def get_issue_metadata(PROJECT_ID, ISSUETYPE):
    # Construct the URL
    url = f"{JIRA_URL}/rest/api/2/issue/createmeta/{PROJECT_ID}/issuetypes/{ISSUETYPE}"

    # HTTP headers with authentication
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # Basic authentication with email and API token
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)

    # Send a GET request to Jira
    response = requests.get(url, headers=headers, auth=auth)

    # Check the response status
    if response.status_code == 200:
        data = response.json()
        # Save the JSON response to a file
        with open(json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)
        logger.info(f"File {json_file_path} updated.")
    else:
        logger.error(f"Error updating {json_file_path}: {response.text}")
        # Quit the program if an error occurs
        exit(1)

def get_screen(screen_id, path):
    try:
        # Get the tabs of a given screen
        def get_tabs(screen_id):
            url = f"{JIRA_URL}/rest/api/3/screens/{screen_id}/tabs"

            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            auth = (JIRA_EMAIL, JIRA_API_TOKEN)
            response = requests.get(url, headers=headers, auth=auth)

            if response.status_code == 200:
                logger.debug(f"Tabs of screen {screen_id} recovered.")
                return response.json()
            else:
                logger.error(f"Error getting tabs for screen {screen_id}: {response.text}")
                exit(1)
        
        # Get the fields of a given tab
        def get_fields(screen_id, tab_id):
            url = f"{JIRA_URL}/rest/api/3/screens/{screen_id}/tabs/{tab_id}/fields"

            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            auth = (JIRA_EMAIL, JIRA_API_TOKEN)
            response = requests.get(url, headers=headers, auth=auth)

            if response.status_code == 200:
                logger.debug(f"Fields of tab {tab_id} in screen {screen_id} recovered.")
                return response.json()
            else:
                logger.error(f"Error getting fields for tab {tab_id} in screen {screen_id}: {response.text}")
                exit(1)

        # Merge the fields of all tabs
        def merge_fields(tabs):
            all_fields = []
            for tab in tabs:
                tab_id = tab['id']
                fields = get_fields(screen_id, tab_id)
                all_fields.extend(fields)
            return all_fields

        # Get the tabs
        tabs = get_tabs(screen_id)
        
        # Merge the fields of all tabs
        merged_fields = merge_fields(tabs)
        
        # Save the merged fields to a file
        with open(path, "w", encoding="utf-8") as f:
            json.dump(merged_fields, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Fields merged and saved to {path}.")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error during data retrieval: {e}")

# Example of function call
# get_screen("11698", "path/to/the/file.json")