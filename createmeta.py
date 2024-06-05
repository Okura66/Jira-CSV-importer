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
    url = f"{JIRA_URL}/rest/api/2/issue/createmeta/{PROJECT_ID}/issuetypes/{ISSUETYPE}"

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
        with open(json_file_path, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)
        logger.info(f"file {json_file_path} updated.")
    else:
        logger.error(f"Error updating {json_file_path}: {response.text}")
        #quit program if error
        exit(1)

def get_screen(screen_id, path):
    try:
        # Récupérer les onglets d'un écran donné
        def get_tabs(screen_id):
            url = f"{JIRA_URL}/rest/api/3/screens/{screen_id}/tabs"

            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            auth = (JIRA_EMAIL, JIRA_API_TOKEN)
            response = requests.get(url, headers=headers, auth=auth)

            if response.status_code == 200:
                logger.debug(f"Les onglets de l'écran {screen_id} ont été récupérés.")
                return response.json()
            else:
                logger.error(f"Error getting tabs for screen {screen_id}: {response.text}")
                exit(1)
        
        # Récupérer les champs d'un onglet donné
        def get_fields(screen_id, tab_id):
            url = f"{JIRA_URL}/rest/api/3/screens/{screen_id}/tabs/{tab_id}/fields"

            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            auth = (JIRA_EMAIL, JIRA_API_TOKEN)
            response = requests.get(url, headers=headers, auth=auth)

            if response.status_code == 200:
                logger.debug(f"Les champs de l'onglet {tab_id} dans l'écran {screen_id} ont été récupérés.")
                return response.json()
            else:
                logger.error(f"Error getting fields for tab {tab_id} in screen {screen_id}: {response.text}")
                exit(1)

        # Fusionner les champs de tous les onglets
        def merge_fields(tabs):
            all_fields = []
            for tab in tabs:
                tab_id = tab['id']
                fields = get_fields(screen_id, tab_id)
                all_fields.extend(fields)
            return all_fields

        # Récupérer les onglets
        tabs = get_tabs(screen_id)
        
        # Fusionner les champs de tous les onglets
        merged_fields = merge_fields(tabs)
        
        # Sauvegarder les champs fusionnés dans un fichier JSON en UTF-8
        with open(path, "w", encoding="utf-8") as f:
            json.dump(merged_fields, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Les champs ont été fusionnés et sauvegardés dans {path}.")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la récupération des données : {e}")

# Exemple d'appel de la fonction
#get_screen("11698", "chemin_vers_le_fichier.json")