import os
import json
import random
import sys
import copy
from datetime import datetime, timedelta
from plexapi.server import PlexServer
from pathlib import Path
import platform

try:
    import config
except ImportError:
    print("Le fichier 'config.py' est manquant. Copiez 'config.py.sample' puis personnalisez-le.")
    sys.exit(1)

from utils import verifier_fichier_existe

python_path = sys.executable  # Donne le chemin du python actif

# Connexion au serveur Plex
baseurl = config.PLEX_BASEURL
token = config.PLEX_TOKEN
plex = PlexServer(baseurl, token)


def main():
    """Point d'entrée du script.

    Ce programme prépare la liste des émissions à générer à partir des
    définitions présentes dans ``emissions_def.json`` et des épisodes
    disponibles dans ``bd_videos.json``. Il attend en paramètre le nombre
    de jours à traiter ainsi qu'une date de départ au format
    ``aaaa-mm-jj``.
    """
    # Vérifier si un nombre suffisant d'arguments a été passé
    if len(sys.argv) < 3:
        print("Usage: python script.py <nombre_de_boucles> <date_aaaa-mm-jj>")
        sys.exit(1)

    try:
        num_loops = int(sys.argv[1])
    except ValueError:
        print("Le premier paramètre doit être un nombre entier.")
        sys.exit(1)

    date_param = sys.argv[2]

    # Vérifier si la date est au bon format (aaaa-mm-jj)
    if not (len(date_param) == 10 and date_param[4] == '-' and date_param[7] == '-'):
        print("Le deuxième paramètre doit être au format 'aaaa-mm-jj'.")
        sys.exit(1)

    # Convertir la date_param en objet datetime
    date_obj = datetime.strptime(date_param, "%Y-%m-%d")

    # Charger les données à partir des fichiers JSON
    verifier_fichier_existe('emissions_def.json')
    verifier_fichier_existe('bd_videos.json')
    emissions_data = load_json_data('emissions_def.json')
    bdvideos_data = load_json_data('bd_videos.json')

    # Traiter les émissions
    emissions_info = process_emissions(num_loops, date_obj, emissions_data, bdvideos_data)

    # Écrire les informations dans un fichier JSON
    write_json_data('listegeneration.json', emissions_data)

    print("Les informations ont été écrites dans listegeneration.json.")

def load_json_data(filename):
    """Charge un fichier JSON et retourne son contenu sous forme de dictionnaire."""
    with open(filename, 'r', encoding='utf-8') as file:
        return json.load(file)

def write_json_data(filename, data):
    """Enregistre les données JSON dans un fichier.

    Une copie profonde des données est utilisée afin de préserver la structure
    originale. La clé ``series`` est retirée pour alléger le fichier de sortie.
    """
    # Créez une copie profonde des données pour éviter de modifier les données originales
    data_copy = copy.deepcopy(data)

    # Supprimez la classe "series" du dictionnaire "data_copy"
    if "series" in data_copy:
        del data_copy["series"]

    # Ouvrir le fichier pour écrire les données JSON
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(data_copy, file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du fichier JSON : {e}")

def process_emissions(num_loops, date_obj, emissions_data, bdvideos_data):
    """Construit la planification des émissions à venir.

    * ``num_loops`` définit le nombre de passages sur la liste des émissions.
    * ``date_obj`` indique la date de diffusion du premier épisode.
    * ``emissions_data`` contient la description des émissions à produire.
    * ``bdvideos_data`` référence les fichiers ou épisodes Plex disponibles.

    La fonction assemble pour chaque émission la liste des segments vidéo à
    utiliser et met à jour l'information sur le prochain épisode à jouer.
    """
    emissions_info = []

    for _ in range(num_loops):
        for emission in emissions_data["emissions"]:
            series_list = []
            videos_list = []
            aincrementer_list = []
            id_plex_list = []

            for segment in emission["segments"]:
                serie_name = segment["série"]

                if serie_name not in ["Fin", "Transitions", "Intros"]:
                    series_list.append(serie_name)

                serie = find_serie(serie_name, bdvideos_data)
                serie_def, ordre_serie = find_serie_def(serie_name, emissions_data)
                print(f"Ordre '{ordre_serie}' '{serie_name}'  ")
                if serie:
                    if ordre_serie == "sequentiel":
                        print(f"sequentiel")
                        prochain_episode = serie_def.get("prochain", 1)
                        video_choisie, id_plex = get_video_path(serie.get("fichiers", [])[prochain_episode - 1])
                        if id_plex:
                            id_plex_list.append(id_plex)
                        prochain_episode += 1
                        print(f"on incrémente")

                        if prochain_episode > serie_def.get("nb_episodes", 1):
                            prochain_episode = 1
                            print(f"on revient a 1 ")

                        serie_def["prochain"] = prochain_episode
                        aincrementer_list.append(serie_name)
                    else:
                        print(f"aleatoire")
                        video_choisie, id_plex = get_video_path(random.choice(serie.get("fichiers", [])))
                        if id_plex:
                            id_plex_list.append(id_plex)
                    videos_list.append(video_choisie)
                else:
                    print(f"La série '{serie_name}' n'a pas été trouvée dans bdvideos_data.")

            # Appliquer map_path pour mapper les chemins pour chaque système d'exploitation
            videos_list = [map_path(video) for video in videos_list]

            description = " | ".join(series_list)
            emission_info = {
                "no": emission["no"],
                "date_diffusion": date_obj.strftime('%Y-%m-%d'),
                "titre": emission["titre"],
                "description": description,
                "fichiers_concatenes": videos_list,
                "a_incrementer": aincrementer_list,
                "genere": False,
                "id_plex": id_plex_list  # Ajouter les identifiants Plex
            }
            emissions_info.append(emission_info)
            date_obj += timedelta(days=1)

    emissions_data["emissions"] = emissions_info
    return emissions_info

def find_serie(serie_name, bdvideos_data):
    """Recherche une série par son nom dans la base vidéo."""
    for series in bdvideos_data.get("series", []):
        if series.get("nom") == serie_name:
            return series
    return None

def find_serie_def(serie_name, emissions_data):
    """Retourne la définition d'une série et son ordre de lecture."""
    for series in emissions_data.get("series", []):
        if series.get("nom") == serie_name:
            return series, series.get("ordre")
    return None, None

def get_video_path(file_entry):
    """Obtient le chemin réel d'un fichier vidéo.

    Si ``file_entry`` commence par ``PLEX-ÉPISODE:``, l'identifiant est
    utilisé pour récupérer le fichier correspondant dans Plex puis le
    chemin est ajusté avec le bon point de montage. La fonction retourne
    le chemin final et éventuellement l'identifiant de l'épisode.
    """
    if file_entry.startswith("PLEX-ÉPISODE:"):
        episode_id = file_entry.split(":")[1]
        episode = plex.library.fetchItem(int(episode_id))
        file_path = episode.media[0].parts[0].file

        # Ajouter le point de montage approprié selon l'OS
        file_path = add_mount_point(file_path)

        return file_path, episode_id
    return map_path(file_entry), None

def add_mount_point(file_path):
    """Ajoute le point de montage selon le système d'exploitation."""
    os_name = platform.system()

    # Ajouter le point de montage en fonction de l'OS
    if os_name == "Windows":
        mount_point = "//MEDIAS/"
    else:
        mount_point = "/mnt/"

    # S'assurer que le chemin reste correct avec /
    return mount_point + file_path.lstrip("/").replace("\\", "/")

def map_path(path):
    """
    Applique le mapping des chemins en fonction de l'OS (Windows ou Linux).
    Les chemins sont déjà au format /, donc on ne change que le point de montage ou partage réseau.
    """
    os_name = config.OS_NAME
    if os_name == "Windows":
        linux_base = config.PATH_MAPPINGS.get('Linux', '/mnt/')
        windows_base = config.PATH_MAPPINGS.get('Windows', '//MEDIAS/')
        if path.startswith(linux_base):
            path = path.replace(linux_base, windows_base, 1)
    # Retourne le chemin modifié (ou non modifié s'il n'y a pas de mapping)
    return path

if __name__ == "__main__":
    main()
