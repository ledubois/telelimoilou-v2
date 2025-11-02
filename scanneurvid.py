import os
import json
import platform
from pathlib import Path
from plexapi.server import PlexServer
import sys

try:
    import config
except ImportError:
    print("Le fichier 'config.py' est manquant. Copiez 'config.py.sample' puis personnalisez-le.")
    sys.exit(1)

from utils import verifier_fichier_existe

python_path = sys.executable  # Donne le chemin du python actif

# Mappings entre chemins Linux et partages réseau Windows
PATH_MAPPINGS = config.PATH_MAPPINGS

# Extensions de fichiers vidéo à rechercher
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mkv', '.mov']

# Connexion au serveur Plex
BASEURL = config.PLEX_BASEURL
TOKEN = config.PLEX_TOKEN
try:
    plex = PlexServer(BASEURL, TOKEN)
except Exception as e:
    print(f"Erreur de connexion à Plex : {e}")
    exit(1)

def display_all_series_ids():
    """
    Affiche toutes les séries dans Plex organisées par bibliothèque avec leurs IDs.
    """
    try:
        libraries = plex.library.sections()
        print("\n--- Liste de toutes les séries organisées par bibliothèque ---\n")
        for library in libraries:
            if library.type == 'show':  # Vérifie si la bibliothèque est de type 'show' (séries)
                print(f"Bibliothèque : {library.title}")
                series = library.all()
                if not series:
                    print("    Aucune série trouvée dans cette bibliothèque.")
                for show in series:
                    print(f"    Série : {show.title} - ID : {show.ratingKey}")
                print()  # Ligne vide pour séparer les bibliothèques
    except Exception as e:
        print(f"Erreur lors de la récupération des séries : {e}")

def scan_directory(path):
    """
    Parcourt récursivement un répertoire et retourne une liste de tous les fichiers vidéo trouvés.
    """
    video_files = []
    for root, _, files in os.walk(path):
        for file in files:
            if any(file.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                # Conserver les chemins avec des slashes même sous Windows
                video_files.append(str(Path(root).as_posix() + '/' + file))
    return sorted(video_files)

def get_plex_episodes(series_id):
    """
    Retourne une liste des identifiants des épisodes pour une série Plex donnée.
    """
    try:
        serie = plex.library.fetchItem(int(series_id))
        episode_ids = [f"PLEX-ÉPISODE:{episode.ratingKey}" for episode in serie.episodes()]
        return episode_ids
    except Exception as e:
        print(f"Erreur lors de la récupération des épisodes pour la série ID {series_id} : {e}")
        return []

def add_mount_point(path, os_name):
    """
    Ajoute le point de montage approprié (Linux ou Windows) aux chemins provenant de `emissions_def.json`.
    """
    if not path.startswith("/mnt/") and not path.startswith("//MEDIAS/"):
        mount_point = PATH_MAPPINGS.get(os_name)
        path = os.path.join(mount_point, path.lstrip("/"))
    return path

def process_series_and_update_json(json_data, os_name):
    """
    Traite les données JSON pour extraire les informations des séries et leurs fichiers vidéo ou identifiants Plex.
    Met à jour le fichier 'emissions_def.json' avec le nombre d'épisodes.
    Applique le mapping des chemins en fonction de l'OS.
    """
    series_data = []  # Liste pour stocker les données des séries

    for series in json_data.get("series", []):
        series_name = series.get("nom")
        series_paths = series.get("chemins", [])
        
        # Initialisation du compteur d'épisodes
        video_files_or_episodes = []

        for path in series_paths:
            if path.startswith("PLEX-SÉRIE:"):
                # Extraire les épisodes depuis Plex
                series_id = path.split(":")[1]
                print(f"Extraction des épisodes depuis Plex pour la série ID: {series_id}")
                video_files_or_episodes.extend(get_plex_episodes(series_id))
            else:
                # Ajouter le point de montage approprié avant de scanner le répertoire
                full_path = add_mount_point(path, os_name)
                print(f"Scanning directory: {full_path}")
                if Path(full_path).exists():
                    video_files_or_episodes.extend(scan_directory(full_path))
                else:
                    print(f"Chemin non trouvé : {full_path}")

        # Mettre à jour la clé nb_episodes dans json_data pour la série correspondante
        series['nb_episodes'] = len(video_files_or_episodes)

        # Ajouter les données de la série à la liste pour bd_videos.json
        series_data.append({
            "nom": series_name,
            "nb_episodes": len(video_files_or_episodes),  # Calcul du nombre d'épisodes
            "fichiers": video_files_or_episodes
        })

    return series_data, json_data  # Retourne la liste des séries pour bd_videos et json_data mis à jour

def save_json_data(data, file_path):
    """
    Sauvegarde les données dans un fichier JSON avec une clé "series".
    """
    wrapped_data = {"series": data}  # Envelopper les données dans une clé "series"
    try:
        with open(file_path, 'w', encoding='utf-8') as json_file:
            json.dump(wrapped_data, json_file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du fichier JSON : {e}")

def save_json_data_nb_episodes_only(updated_json_data, original_json_data, file_path):
    """
    Sauvegarde uniquement les informations mises à jour sur le nombre d'épisodes
    dans le fichier JSON, sans toucher aux autres informations.
    """
    try:
        for updated_series in updated_json_data.get("series", []):
            # Rechercher la série correspondante dans le JSON d'origine
            for original_series in original_json_data.get("series", []):
                if original_series['nom'] == updated_series['nom']:
                    # Mettre à jour uniquement le nb_episodes
                    original_series['nb_episodes'] = updated_series['nb_episodes']

        # Sauvegarder les modifications dans le fichier JSON d'origine
        with open(file_path, 'w', encoding='utf-8') as json_file:
            json.dump(original_json_data, json_file, ensure_ascii=False, indent=4)

    except Exception as e:
        print(f"Erreur lors de la sauvegarde du fichier JSON : {e}")

def main():
    """Analyse les répertoires de séries et met à jour les fichiers JSON."""
    # Déterminer le système d'exploitation
    os_name = config.OS_NAME
    print(f"Système d'exploitation détecté : {os_name}")

    # Afficher toutes les séries avec leurs IDs organisées par bibliothèque
    display_all_series_ids()

    # Chemin vers le fichier JSON d'origine et de destination dans le répertoire courant
    JSON_FILE_PATH = Path.cwd() / "emissions_def.json"
    VIDEO_FILES_JSON_PATH = Path.cwd() / "bd_videos.json"

    verifier_fichier_existe(str(JSON_FILE_PATH))

    # Lecture du fichier JSON d'origine
    print(f"Lecture du fichier JSON d'origine : {JSON_FILE_PATH}")
    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier JSON : {e}")
        exit(1)

    # Traitement des séries et mise à jour de json_data
    print("Traitement des séries et mise à jour du nombre d'épisodes...")
    series_data, updated_json_data = process_series_and_update_json(data, os_name)

    # Sauvegarde des données dans le fichier JSON d'origine (mise à jour uniquement de nb_episodes)
    print(f"Sauvegarde des données mises à jour dans le fichier JSON d'origine (nb_episodes uniquement) : {JSON_FILE_PATH}")
    save_json_data_nb_episodes_only(updated_json_data, data, JSON_FILE_PATH)

    # Sauvegarde des données dans le fichier JSON de destination (bd_videos.json)
    print(f"Sauvegarde des données dans le fichier JSON de destination : {VIDEO_FILES_JSON_PATH}")
    save_json_data(series_data, VIDEO_FILES_JSON_PATH)

    print("Le programme a terminé avec succès.")

if __name__ == "__main__":
    main()
