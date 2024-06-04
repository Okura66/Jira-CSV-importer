import logging
# Configure logging
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

# Obtention du chemin absolu du répertoire du script
script_dir = os.path.dirname(os.path.realpath(__file__))
# Concaténation du chemin absolu avec le nom du fichier JSON
json_file_path = os.path.join(script_dir, "schema.json")

# Configuration
JIRA_URL = os.getenv("JIRA_URL")  # URL de l'instance JIRA
JIRA_EMAIL = os.getenv("JIRA_EMAIL")  # Email de l'utilisateur JIRA
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")  # Jeton d'API de l'utilisateur JIRA

def get_issue_metadata(PROJECT_ID, ISSUETYPE):
    # Construction de l'URL
    url = f"{JIRA_URL}/rest/api/3/issue/createmeta/{PROJECT_ID}/issuetypes/{ISSUETYPE}"

    # En-têtes HTTP avec l'authentification
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # Authentification basique avec l'email et le jeton d'API
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)

    # Envoi de la requête GET à JIRA
    response = requests.get(url, headers=headers, auth=auth)

    # Vérification du statut de la réponse
    if response.status_code == 200:
        data = response.json()
        # Enregistrement de la réponse JSON dans le fichier
        with open(json_file_path, "w") as json_file:
            json.dump(data, json_file, indent=4)
        logger.info(f"file {json_file_path} updated.")
    else:
        logger.error(f"Error updating {json_file_path}: {response.text}")
        #quit program if error
        exit(1)

def get_screen(id, json_file_path):
    # Construction de l'URL
    url = f"{JIRA_URL}/rest/api/3/screens/{id}/availableFields"

    # En-têtes HTTP avec l'authentification
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # Authentification basique avec l'email et le jeton d'API
    auth = (JIRA_EMAIL, JIRA_API_TOKEN)

    # Envoi de la requête GET à JIRA
    response = requests.get(url, headers=headers, auth=auth)

    # Vérification du statut de la réponse
    if response.status_code == 200:
        data = response.json()
        # Enregistrement de la réponse JSON dans le fichier
        with open(json_file_path, "w") as json_file:
            json.dump(data, json_file, indent=4)
        logger.info(f"file {json_file_path} updated.")
    else:
        logger.error(f"Error updating {json_file_path}: {response.text}")
        #quit program if error
        exit(1)