# Jira CSV Importer

This script allows you to import data from a CSV file into Jira using the Jira REST API.
![image](https://github.com/Okura66/Jira-CSV-importer/blob/main/Sch%C3%A9ma%20Python.jpg)

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

You can customize the mapping between CSV columns and Jira fields by modifying the `csv_to_jira_key_map` dictionary in the script. Add or remove key-value pairs to map CSV column names to Jira field names.

## Logging

The script logs its progress and any errors to a file named `.log` in the same directory as the script.
You can set different logging level (see [logging library](https://docs.python.org/3/library/logging.html#logging-levels)) .
