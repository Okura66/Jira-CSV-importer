import os
import logging
# Configure logging
script_dir = os.path.dirname(os.path.abspath(__file__))
log_file_path = os.path.join(script_dir, 'scare.log')

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename=log_file_path,
    encoding='utf-8',
    filemode='w',
    format='%(asctime)s %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S',
    level=logging.DEBUG
)

import requests
import json

from dotenv import load_dotenv

# https://developer.atlassian.com/server/jira/platform/jira-rest-api-example-discovering-meta-data-for-creating-issues-6291669/

# Load environment variables from .env file
load_dotenv()

# Concatenate the absolute path with the JSON file name
json_file_path = os.path.join(script_dir, "schema.json")

# Configuration
JIRA_URL = os.getenv("JIRA_URL")  # URL of the JIRA instance
JIRA_EMAIL = os.getenv("JIRA_EMAIL")  # Email of the JIRA user
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")  # API token of the JIRA user

def get_issue_metadata(PROJECT_ID, ISSUETYPE):
    # Construct the base URL for the API request
    base_url = f"{JIRA_URL}/rest/api/2/issue/createmeta/{PROJECT_ID}/issuetypes/{ISSUETYPE}"

    # HTTP headers with authentication
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # Basic authentication with email and API token
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)

    # Initialize variables for pagination
    start_at = 0
    max_results = 50  # Number of items per page
    all_data = {
        "fields": [],
        "maxResults": 0,
        "startAt": 0,
        "total": 0
    }

    while True:
        # Construct the URL with query parameters for pagination
        url = f"{base_url}?startAt={start_at}&maxResults={max_results}"

        # Send GET request to JIRA
        response = requests.get(url, headers=headers, auth=auth)

        # Check the response status
        if response.status_code == 200:
            data = response.json()

            # Update the combined data object
            all_data["fields"].extend(data.get("fields", []))
            all_data["maxResults"] = data.get("maxResults", 0)
            all_data["startAt"] = data.get("startAt", 0)
            all_data["total"] = data.get("total", 0)

            # Check if there's more data to fetch
            if len(data.get("fields", [])) < max_results or all_data["startAt"] >= all_data["total"]:
                break  # No more data to fetch

            start_at += max_results  # Move to the next page
        else:
            logger.error(f"Error updating {json_file_path}: {response.text}")
            exit(1)

    # Save the combined JSON response to the file
    with open(json_file_path, "w", encoding="utf-8") as json_file:
        json.dump(all_data, json_file, indent=4, ensure_ascii=False)

    logger.info(f"File {json_file_path} updated with all pages of data.")
    
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
                logger.debug(f"Tabs for screen {screen_id} have been retrieved.")
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
                logger.debug(f"Fields for tab {tab_id} in screen {screen_id} have been retrieved.")
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
        
        # Save the merged fields to a JSON file in UTF-8
        with open(path, "w", encoding="utf-8") as f:
            json.dump(merged_fields, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Fields have been merged and saved to {path}.")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error retrieving data: {e}")

# Example of function call
#get_screen("11698", "path_to_file.json")
