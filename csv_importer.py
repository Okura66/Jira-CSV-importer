############################################################################################
#  Title: CSV jira importer                                                                #
#  Version: 1.6                                                                            #
#  Date: 11/06/2024                                                                        #
#  Author: Axel MONTZAMIR                                                                  #
#  Description: This script reads data from a CSV file and creates or updates Jira issues. #
############################################################################################

import logging # Import the logging module for logging messages
logger = logging.getLogger(__name__)
logging.basicConfig(
    filename='.log',
    encoding='utf-8',
    filemode='w',
    format='%(asctime)s %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S',
    level=logging.INFO
)
import os
import json # JSON module for parsing JSON data
import time # Time module for sleep function
import re # Regular expressions
import gc # Garbage collector
import threading # Threading support for parallel processing
import pandas as pd # Data manipulation library
import requests # HTTP requests library
from requests.auth import HTTPBasicAuth # HTTP Basic authentication
from tqdm import tqdm # Progress bar for processing rows
from dotenv import load_dotenv # Load environment variables from .env file
from concurrent.futures import ThreadPoolExecutor, as_completed # Thread pool executor for parallel processing
from createmeta import get_issue_metadata, get_screen # Import functions from createmeta.py

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_API_ENDPOINT = f"{JIRA_URL}/rest/api/3/issue/"
SCREEN_CREATE = os.getenv("SCREEN_CREATE")
SCREEN_EDIT = os.getenv("SCREEN_EDIT")
PROJECT_ID = os.getenv("PROJECT_ID")
ISSUETYPE_ID = os.getenv("ISSUETYPE_ID")
if not all([JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN, SCREEN_CREATE, SCREEN_EDIT, PROJECT_ID, ISSUETYPE_ID]):
    logger.error("Please set environment variables")
    exit(1)

script_dir = os.path.dirname(os.path.abspath(__file__))
csv_file_path = os.path.join(script_dir, 'input.csv')
screen_create_path = os.path.join(script_dir, "screen_create.json")
screen_edit_path = os.path.join(script_dir, "screen_edit.json")

with open(os.path.join(script_dir, 'schema.json')) as schema_file:
        schema = json.load(schema_file)

with open(screen_create_path) as screen_create_file:
        screen_create = json.load(screen_create_file)

with open(screen_edit_path) as screen_edit_file:
        screen_edit = json.load(screen_edit_file)

# Return the type of the field and if array return item type
def get_field_type(field_name):
    for field in schema["fields"]:
        if field["name"] == field_name or field["fieldId"] == field_name or field["key"] == field_name:
            if field["schema"]["type"] == "array":
                return field["schema"]["type"] + " of " + field["schema"]["items"]
            return field["schema"]["type"]
        
#verify if field is present in schema
def check_schema(field_name):
    for field in schema["fields"]:
        if field["name"] == field_name or field["fieldId"] == field_name or field["key"] == field_name:
            return True
    return False

def check_field(field_name, screen_type):
    if not field_name or screen_type not in ["create", "edit"]:
        logger.error("Invalid field name or screen type")
        return False
    if field_name in field_exception:
        return True
    
    screen = screen_create if screen_type == "create" else screen_edit
    for field in screen:
        if field["id"] == field_name or field["name"] == field_name:
            return True
    return False

field_exception = ["due_date", "summary", "assignee", "labels", "reporter"]

# This inner function replaces matched URLs with the appropriate JSON structure
def convert_urls_to_json_structure(text):
    def replace_url(match):
        url = match.group(0) # Extract the matched URL
        if url.startswith('http') or url.startswith('https'):
            link_type = 'link'
            display_text = url # Display full URL for HTTP/HTTPS links
        elif url.startswith('mailto:'):
            link_type = 'link'
            display_text = url.replace('mailto:', '') # Remove 'mailto:' prefix for display
        elif url.startswith('tel:'):
            link_type = 'link'
            display_text = url.replace('tel:', '') # Remove 'tel:' prefix for display
        else:
            return {"type": "text", "text": url} # Return as plain text if it doesn't match the above patterns

        # Return the JSON structure for the URL with appropriate link type and display text
        return {
            "type": "text",
            "text": display_text,
            "marks": [
                {
                    "type": link_type,
                    "attrs": {
                        "href": url # The actual URL
                    }
                }
            ]
        }

    # Regular expression pattern to match URLs
    url_pattern = re.compile(r'(https?://\S+|mailto:\S+|tel:\S+)')
    parts = [] # List to hold the JSON parts
    last_end = 0 # Track the end of the last match

    # Iterate over all matches of the URL pattern in the text
    for match in url_pattern.finditer(text):
        start, end = match.span() # Get the start and end positions of the match
        if last_end < start:
            # Append text before the URL match
            parts.append({"type": "text", "text": text[last_end:start]})
        # Append the JSON structure for the URL
        parts.append(replace_url(match))
        last_end = end # Update the last_end position

    if last_end < len(text):
        # Append any remaining text after the last URL match
        parts.append({"type": "text", "text": text[last_end:]})

    # Wrap the parts in a paragraph and return as a list
    return [{
        "type": "paragraph",
        "content": parts
    }]

# Initialize the issue data with project ID and issue type ID
def create_jira_issue(row):
    issue_data = {
        "fields": {
            "project": {
                "id": PROJECT_ID
            },
            "issuetype": {
                "id": ISSUETYPE_ID
            }
        }
    }

    # Iterate over each column in the CSV row
    for csv_field in row.index:
        value = row[csv_field] # Get the value for the current field

        # Log the processing details for debugging
        logger.debug(f"Processing field: {csv_field}, Value: {value}, Schema Check: {check_schema(csv_field)}")
        logger.debug(f"Field Type: {get_field_type(csv_field)}")

        # Check if the value is not null and the field exists in the schema or is in the exception list
        if pd.notna(value) and (check_schema(csv_field) or csv_field in field_exception):
            field_type = get_field_type(csv_field) # Get the field type from the schema

            # Log additional debug information
            logger.debug(f"Edit screen : {check_field(csv_field, 'edit')}, Create screen : {check_field(csv_field, 'create')}")

            # Check if the field should be included based on the issue key and screen type (create/edit)
            if (pd.notna(row["issuekey"]) and check_field(csv_field, "edit")) or (pd.isna(row["issuekey"]) and check_field(csv_field, "create")):
                # Populate the issue data based on the field type
                if field_type == "array of string":
                    issue_data["fields"][csv_field] = value.split(" ") # Split the value into a list of strings
                elif field_type == "array of option":
                    issue_data["fields"][csv_field] = [{"value": v} for v in value.split(" ")] # Create a list of option objects
                elif field_type == "option":
                    issue_data["fields"][csv_field] = {"value": value} # Create a single option object
                elif field_type == "date":
                    issue_data["fields"][csv_field] = value # Directly assign the date value
                elif csv_field == "description":
                    # Convert URLs in the description to the JSON structure
                    issue_data["fields"][csv_field] = {
                        "type": "doc",
                        "version": 1,
                        "content": convert_urls_to_json_structure(value)
                    }
                elif field_type == "user":
                    issue_data["fields"][csv_field] = {"id": value} # Assign the user ID
                elif field_type == "datetime":
                    issue_data["fields"][csv_field] = value + "T00:00:00.000Z" # Format the datetime value in ISO 8601 format
                else:
                    issue_data["fields"][csv_field] = value # Assign the value directly for other types

    # Log the final issue data for debugging
    logger.debug(f"Final issue data: {issue_data}")

    if pd.notna(row["issuekey"]):
        issue_key = row["issuekey"]
        jira_api_endpoint = f"{JIRA_URL}/rest/api/3/issue/{issue_key}"
        response = requests.put(
            jira_api_endpoint,
            json=issue_data,
            auth=HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN),
            headers={"Content-Type": "application/json"}
        )
        operation = "updated"
    else:
        jira_api_endpoint = f"{JIRA_URL}/rest/api/3/issue"
        response = requests.post(
            jira_api_endpoint,
            json=issue_data,
            auth=HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN),
            headers={"Content-Type": "application/json"}
        )
        operation = "created"
    
    return response, operation, issue_key if pd.notna(row["issuekey"]) else None, jira_api_endpoint, issue_data

def handle_response(response, operation, issue_key, jira_api_endpoint, issue_data):
    if response.status_code == 403: # 403: Forbidden
        logger.error("Forbidden. Please check if the user has the necessary permissions. Aborting...")
        exit(1)
    elif response.status_code in [200, 204]:  # 200/204: updated
        logger.info(f"Issue {operation} successfully({response.status_code}): {JIRA_URL}/browse/{issue_key}")
    elif response.status_code == 201: # 201: Created
        logger.info(f"Issue {operation} successfully({response.status_code}): {JIRA_URL}/browse/{response.json()['key']}")
    elif response.status_code in [502, 504, 408]: # 502: Bad Gateway, 504: Gateway Timeout, 408: Request Timeout
        logger.warning("Timeout occurred while creating issue. Retrying...")
        for _ in range(2):
            time.sleep(10)
            response = requests.post(
                jira_api_endpoint,
                json=issue_data,
                auth=HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN),
                headers={"Content-Type": "application/json"}
            )
            if response.status_code in [200, 204]:
                logger.info(f"Issue {operation} successfully({response.status_code}): {JIRA_URL}/browse/{issue_key}")
                break
            elif response.status_code == 201:
                logger.info(f"Issue {operation} successfully({response.status_code}): {JIRA_URL}/browse/{response.json()['key']}")
                break
        else:
            logger.error(f"Failed to {operation} issue({response.status_code}): {response.text}")
    elif response.status_code == 429: # 429: Too Many Requests
        # Retry indefinitely until the request is successful, with a delay of 1 minute
        logger.warning("Too many requests. Retrying...")
        while response.status_code == 429:
            time.sleep(60)
            response = requests.post(
                jira_api_endpoint,
                json=issue_data,
                auth=HTTPBasicAuth(JIRA_USERNAME, JIRA_API_TOKEN),
                headers={"Content-Type": "application/json"}
            )
    else:
        logger.error(f"Failed to {operation} issue({response.status_code}): {response.text}")

def process_row(row, stop_event, stats, pbar):
    if stop_event.is_set():
        return

    try:
        response, operation, issue_key, jira_api_endpoint, issue_data = create_jira_issue(row)
        handle_response(response, operation, issue_key, jira_api_endpoint, issue_data)
        if response.status_code in [200, 201, 204]:
            stats['success'] += 1
        else:
            stats['failed'] += 1
    except Exception as e:
        logger.error(f"Error processing row: {e}")
        stop_event.set()
        stats['failed'] += 1
    finally:
        pbar.update(1)

def main():
    # Retrieve and update issue metadata and screen configurations
    get_issue_metadata(PROJECT_ID, ISSUETYPE_ID)
    get_screen(SCREEN_CREATE, screen_create_path)
    get_screen(SCREEN_EDIT, screen_edit_path)
    
    stop_event = threading.Event() # Event used to signal the threads to stop processing
    chunk_size = 1000 # Define the chunk size for reading the CSV file in parts
    total_rows = len(pd.read_csv(csv_file_path)) # Calculate the total number of rows in the CSV file
    stats = {'success': 0, 'failed': 0} # Dictionary to keep track of success and failure counts

    try:
        # Create a ThreadPoolExecutor to manage multiple threads
        with ThreadPoolExecutor(max_workers=5) as executor, tqdm(total=total_rows, desc="Processing rows", unit="issues") as pbar:
            for chunk in pd.read_csv(csv_file_path, chunksize=chunk_size):
                # Submit tasks for each row in the current chunk
                futures = {executor.submit(process_row, row, stop_event, stats, pbar): index for index, row in chunk.iterrows()}
                try:
                    # Wait for the tasks to complete and handle their results
                    for future in as_completed(futures):
                        future.result()  # This will raise any exceptions caught during processing
                except KeyboardInterrupt:
                    # Handle the keyboard interrupt (CTRL + C) by setting the stop event
                    logger.info("Keyboard interrupt received. Stopping...")
                    stop_event.set()
                    break
                finally:
                    # Cancel all futures that are still running
                    for future in futures:
                        future.cancel()
                    executor.shutdown(wait=False) # Shutdown the executor to stop accepting new tasks
                    gc.collect() # Collect garbage to free up memory
                    break

    except KeyboardInterrupt:
        # Handle keyboard interrupt (CTRL + C) at the outer level
        logger.info("Keyboard interrupt received. Stopping...")
        stop_event.set()
        executor.shutdown(wait=False)
        gc.collect()

    total_processed = stats['success'] + stats['failed'] # Calculate the total number of processed rows
    success_percentage = (stats['success'] / total_processed) * 100 if total_processed else 0 # Calculate the percentage of successful operations
    failed_percentage = (stats['failed'] / total_processed) * 100 if total_processed else 0 # Calculate the percentage of failed operations

    # Log the final processing statistics
    logger.info(f"Completed processing {total_processed}/{total_rows} rows.")
    logger.info(f"Total issues created/updated: {stats['success']} ({success_percentage:.2f}%)")
    logger.info(f"Total issues failed: {stats['failed']} ({failed_percentage:.2f}%)")
    logger.info("Script execution completed.")

if __name__ == "__main__":
    main()