############################################################################################
#  Title: CSV jira importer                                                                #
#  Version: 1.0                                                                            #
#  Date: 31/05/2024                                                                        #
#  Author: Axel MONTZAMIR                                                                  #
#  Description: This script reads data from a CSV file and creates or updates Jira issues. #
############################################################################################

import logging
# Configure logging
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
import json
import time
import threading
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from tqdm import tqdm
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
from createmeta import get_issue_metadata, get_screen

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
data_frame = pd.read_csv(csv_file_path)
screen_create_path = os.path.join(script_dir, "screen_create.json")
screen_edit_path = os.path.join(script_dir, "screen_edit.json")

#create or update json schema and screen files
get_issue_metadata(PROJECT_ID, ISSUETYPE_ID)
get_screen(SCREEN_CREATE, screen_create_path)
get_screen(SCREEN_EDIT, screen_edit_path)

# Load schemas and screens once
with open(os.path.join(script_dir, 'schema.json')) as schema_file:
    schema = json.load(schema_file)

with open(screen_create_path) as screen_create_file:
    screen_create = json.load(screen_create_file)

with open(screen_edit_path) as screen_edit_file:
    screen_edit = json.load(screen_edit_file)

def get_field_type(field_name):
    for field in schema["fields"]:
        if field["name"] == field_name or field["fieldId"] == field_name or field["key"] == field_name:
            return field["schema"]["type"]
    return None

def check_field(field_name, screen_type):
    if not field_name or screen_type not in ["create", "edit"]:
        return False
    if field_name in ["duedate", "summary", "assignee", "description", "labels", "reporter"]:
        return True
    
    screen = screen_create if screen_type == "create" else screen_edit
    for field in screen:
        if field["name"] == field_name or field["id"] == field_name:
            return True
    return False

'''csv_to_jira_key_map = {
    "issuekey": "issuekey",
    "Labels": "labels",
    "Summary": "summary",
    "Assignee Id": "assignee",
    "Reporter Id": "reporter",
    "Description": "description"
}'''

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
    
    for csv_field, jira_field in zip(data_frame.columns, data_frame.columns):
    #for csv_field, jira_field in csv_to_jira_key_map.items():
        value = row[csv_field]
        if pd.notna(value):
            field_type = get_field_type(jira_field)
            
            logger.debug(f"Processing field: {jira_field}, Value: {value}, Field Type: {field_type}")
            
            if (pd.notna(row["issuekey"]) and check_field(jira_field, 'create')) or (pd.isna(row["issuekey"]) and check_field(jira_field, 'edit')):
                if field_type == "array":
                    #replace space with comma "," for array fields
                    issue_data["fields"][jira_field] = value.split(" ")
                elif field_type == "option":
                    issue_data["fields"][jira_field] = {"value": value}
                elif field_type == "date":
                    issue_data["fields"][jira_field] = value
                elif jira_field == "description":
                    issue_data["fields"][jira_field] = {
                        "type": "doc",
                        "version": 1,
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": value}]
                        }]
                    }
                elif field_type == "user":
                    issue_data["fields"][jira_field] = {"id": value}
                elif field_type == "datetime":
                    issue_data["fields"][jira_field] = value + "T00:00:00.000Z"
                else:
                    issue_data["fields"][jira_field] = value

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
    
    logger.debug(f"Request URL: {jira_api_endpoint}")
    logger.debug(f"Request Payload: {json.dumps(issue_data, indent=2)}")
    logger.debug(f"Response Status Code: {response.status_code}")
    logger.debug(f"Response Text: {response.text}")

    return response, operation, issue_key if pd.notna(row["issuekey"]) else None, jira_api_endpoint, issue_data

def handle_response(response, operation, issue_key, jira_api_endpoint, issue_data):
    if response.status_code == 403:  # 403: Forbidden
        logger.error("Forbidden. Please check if the user has the necessary permissions. Aborting...")
        exit(1)
    elif response.status_code in [200, 204]:  # 200/204: updated
        logger.info(f"Issue {operation} successfully({response.status_code}): {JIRA_URL}/browse/{issue_key}")
    elif response.status_code == 201:  # 201: Created
        logger.info(f"Issue {operation} successfully({response.status_code}): {JIRA_URL}/browse/{response.json()['key']}")
    elif response.status_code in [502, 504, 408]:  # 502: Bad Gateway, 504: Gateway Timeout, 408: Request Timeout
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
    elif response.status_code == 429:  # 429: Too Many Requests
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

def process_row(row, stop_event):
    if stop_event.is_set():
        return

    try:
        response, operation, issue_key, jira_api_endpoint, issue_data = create_jira_issue(row)
        handle_response(response, operation, issue_key, jira_api_endpoint, issue_data)
    except Exception as e:
        logger.error(f"Error processing row: {e}")
        stop_event.set()

stop_event = threading.Event()

with ThreadPoolExecutor(max_workers=1) as executor:
    futures = {executor.submit(process_row, row, stop_event): index for index, row in data_frame.iterrows()}
    try:
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing rows"):
            future.result()  # Will raise exceptions if any occurred
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Stopping...")
        stop_event.set()