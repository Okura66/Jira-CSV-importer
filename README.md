# Jira CSV Importer

this script allows you to create or update Jira issues from a CSV file. The script reads data from the CSV file and creates or updates Jira issues based on the data provided. The script uses the Jira REST API to interact with Jira. The script supports multi-threading to process multiple issues concurrently.

![image](https://github.com/Okura66/Jira-CSV-importer/blob/main/Sch%C3%A9ma%20Python.jpg)

⚠️ **Warning:** This script will create or update Jira issues based on the data provided in the CSV file. Please make sure to review the data before proceeding.
Generation of the CSV file is not covered in this script. Please make sure to generate the CSV file with the correct data and column names before running this script.
The script is design to be trigger by a cron job to automate the process of creating or updating Jira issues from a CSV file.

## TODO
- [x] Auto define fields type from schema
- [x] Check is field is available in create/edit screen
- [x] Create or update issue
- [x] Handle response status, logging, error handling
- [x] Keyboard interrupt
- [x] Multi-threading
- [x] Test with different field types (array, option, date, user, datetime)\
:warning: URL field can return error with correct value, it's a Jira bug, you can try tro use v2 of the API instead of v3.
- [x] Test with large CSV file (80000+ issues created/updated successfully)
- [ ] Multi-project and issue type support

## Prerequisites

Before running the script, make sure you have the following:

- Python 3 installed on your machine.
- Required Python packages installed. You can install them by running the following command:

    ```
    pip install pandas requests tqdm python-dotenv
    ```

- Jira account with API access. Obtain the following information from your Jira account:

    - Jira URL
    - Jira email
    - Jira API token

## Configuration

Before running the script, you need to configure the following environment variables:

- `JIRA_URL`: The URL of your Jira instance.
- `JIRA_EMAIL`: Your Jira email address.
- `JIRA_API_TOKEN`: Your Jira API token.
- `SCREEN_CREATE`: The screen ID for creating issues in Jira.
- `SCREEN_EDIT`: The screen ID for editing issues in Jira.

## Usage

1. Place your CSV file named `input.csv` in the same directory as the script.
2. Run the script using the following command:

     ```
     python csv_importer.py
     ```

3. The script will read the CSV file and create or update Jira issues based on the data.

## Customization

ℹ️ csv_to_jira_key_map is a dictionary that maps the column names in the CSV file to the corresponding Jira field names. You can update this dictionary to map the column names in your CSV file to the correct Jira field names. But actually the script use the column names as Jira field names, you can uncomment the csv_to_jira_key_map and use it if you want to map the column names to different Jira field names...

## Logging

The script logs its progress and any errors to a file named `.log` in the same directory as the script.\
You can set different logging level (see [logging library](https://docs.python.org/3/library/logging.html#logging-levels)).
