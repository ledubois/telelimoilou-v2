import os
import shutil
import subprocess
import datetime
import plexapi
from plexapi.server import PlexServer
import json
import platform
import tempfile
import sys
from pathlib import Path
try:
    import config
except ImportError:
    print("Le fichier 'config.py' est manquant. Copiez 'config.py.sample' puis personnalisez-le.")
    sys.exit(1)

from utils import verifier_fichier_existe

# Détecter le système d'exploitation
os_name = config.OS_NAME
python_path = sys.executable  # Donne le chemin du python actif

# Chemin de destination pour les vidéos générées
destination_dir = str(config.TVLIMOILOU_DIR)

# Connexion au serveur Plex
# Connexion au serveur Plex
baseurl = config.PLEX_BASEURL
token = config.PLEX_TOKEN

plex = None
userplex = None

try:
    plex = PlexServer(baseurl, token)
    userplex = plex.switchUser("Les filles ")
except Exception as e:
    print(f"Erreur de connexion à Plex : {e}")
    print("Le script continue sans accès à Plex.")

nomjour = datetime.datetime.now().strftime('%A')

# Chemin du répertoire contenant les scripts
script_dir = Path(__file__).parent.resolve()

# Chemin du répertoire temporaire /transcode et /genmessage
transcode_dir = config.TRANSCODE_DIR
genmessage_dir = config.GENMESSAGE_DIR

# Chemin du fichier listegeneration.json
listegeneration_path = script_dir / "listegeneration.json"

# Nom de la section Plex
section_name = 'Télé Limoilou'
title_contains = 'Émission'  # Terme à rechercher dans le titre

# Fonction pour écrire dans le fichier de journal
def write_to_log(message):
    """Ajoute une entrée datée dans ``log.txt``."""
    date_jour = datetime.datetime.now().strftime("%Y-%m-%d")
    with open("log.txt", "a") as log_file:
        log_file.write(date_jour + " - " + message + "\n")

# Fonction exécutée par le script
def execute_script():
    """Orchestre les différentes étapes de génération des émissions."""
    # Lire le fichier listegeneration.json
    verifier_fichier_existe(str(listegeneration_path))
    verifier_fichier_existe('emissions_def.json')
    with open(listegeneration_path, 'r', encoding='utf-8') as listegeneration_file:
        listegeneration_data = json.load(listegeneration_file)

    # Vérifier si l'une des instances d'émissions a la clé "genere" égale à "false" ou si le jour n'est pas dimanche
    if any(emission.get("genere") == False for emission in listegeneration_data.get("emissions", [])) and nomjour != "Sunday":
        write_to_log("L'une des instances d'émissions a la clé 'genere' égale à 'false'. Les étapes 2 et 3 ne seront pas exécutées.")
    else:
        # Étape 2: Exécuter le script scanneurvid.py
        scanneurv_script = script_dir / "scanneurvid.py"
        subprocess.run([python_path, str(scanneurv_script)])
        write_to_log("Script scanneurvid.py exécuté")

        # Étape 3: Exécuter generer.py avec les paramètres spécifiés
        date_format = datetime.datetime.now().strftime("%Y-%m-%d")
        generer_emissions_script = script_dir / "generer.py"
        subprocess.run([python_path, str(generer_emissions_script), "1", date_format])
        write_to_log(f"Script generer.py exécuté avec les paramètres: 1 {date_format}")

    # Étape 0 : Vérifier si la vidéo a été regardée ou non
    
    arreter = True
    movies = userplex.library.section(section_name)
    for video in movies.search(title_contains):
        pourcent_joue = video.viewOffset / video.duration * 100
        print(pourcent_joue)
        if pourcent_joue > 33:
            arreter = False 

    movies = plex.library.section(section_name)
    for video in movies.search(title_contains):
        pourcent_joue = video.viewOffset / video.duration * 100
        print(pourcent_joue)
        if pourcent_joue > 33:
            arreter = False    

    if userplex.library.section('Télé Limoilou').search(title='Émission'):
        if userplex.library.section('Télé Limoilou').search(title='Émission', unwatched=False):
            # arrêter le script
            arreter = False
    else:                       #si n'existe pas il faut transcoder
        arreter = False
 
    if plex.library.section('Télé Limoilou').search(title='Émission'):
        if plex.library.section('Télé Limoilou').search(title='Émission', unwatched=False):
            # arrêter le script
            arreter = False
 


    if arreter:
        write_to_log("La vidéo n'a pas été regardée. Le script s'arrête.")
        return 

    # Supprimer les fichiers de plus de 7 jours dans le répertoire backup et sauvegarder les fichiers actuels

    # Création du répertoire backup s'il n'existe pas
    backup_dir = script_dir / "backup"

    # Vérifier si le répertoire existe déjà
    dir_existed = backup_dir.exists()

    # Créer le répertoire s'il n'existe pas
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Effectuer le chmod uniquement si le répertoire n'existait pas
    if not dir_existed and os_name == "Linux":
        # Linux/Mac : Lecture et écriture pour tout le monde (mode 777 pour répertoire)
        os.chmod(backup_dir, 0o777)

    # Délai en jours pour la suppression
    delai_jours = 7

    # Parcourir les fichiers dans le répertoire backup pour supprimer ceux de plus de 7 jours
    for backup_file in backup_dir.iterdir():
        if backup_file.is_file():  # Vérifier si c'est un fichier
            age_fichier = (datetime.datetime.now() - datetime.datetime.fromtimestamp(backup_file.stat().st_mtime)).days
            if age_fichier > delai_jours:
                backup_file.unlink()  # Supprimer le fichier
                write_to_log(f"Fichier supprimé: {backup_file} (âge: {age_fichier} jours)")

    # Sauvegarde des fichiers listegeneration.json et emissions_def.json
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    listegeneration_backup = backup_dir / f"{current_datetime}_listegeneration.json"
    emissions_def_backup = backup_dir / f"{current_datetime}_emissions_def.json"
    emissions_def_path = script_dir / "emissions_def.json"

    shutil.copyfile(listegeneration_path, listegeneration_backup)
    write_to_log(f"Fichier listegeneration.json sauvegardé dans {listegeneration_backup}")

    if emissions_def_path.exists():
        shutil.copyfile(emissions_def_path, emissions_def_backup)
        write_to_log(f"Fichier emissions_def.json sauvegardé dans {emissions_def_backup}")
    else:
        write_to_log("Fichier emissions_def.json non trouvé, pas de sauvegarde effectuée.")


    # Étape 1: Supprimer les fichiers dans /transcode et genmessage s'ils existent
    if transcode_dir.exists():
        shutil.rmtree(transcode_dir)
        write_to_log(f"Répertoire supprimé: {transcode_dir}")
        
    if genmessage_dir.exists():
        shutil.rmtree(genmessage_dir)
        write_to_log(f"Répertoire supprimé: {genmessage_dir}")

    # Recréer les répertoires /transcode et /genmessage
    transcode_dir.mkdir(parents=True, exist_ok=True)
    write_to_log(f"Répertoire créé: {transcode_dir}")
    if os_name == "Linux" :
    	# Linux/Mac : Lecture et écriture pour tout le monde (mode 777 pour répertoire)
    	os.chmod(transcode_dir, 0o777)

    genmessage_dir.mkdir(parents=True, exist_ok=True)
    write_to_log(f"Répertoire créé: {genmessage_dir}")

    # Étape 3: Créer le message personnalisé avec genvidmessage.py
    genvidmessage_script = script_dir / "genvidmessage.py"
    subprocess.run([python_path, str(genvidmessage_script)])
    write_to_log("Script genvidmessage.py exécuté")
    
    # Étape 4: Exécuter transcode.py avec le paramètre spécifié
    transcode_script = script_dir / "transcode.py"
    subprocess.run([python_path, str(transcode_script)])
    write_to_log("Script transcode.py exécuté")

    # Étape 5: Supprimer tous les fichiers MP4 s'ils existent dans destination_dir
    for file_name in os.listdir(destination_dir):
        if file_name.endswith(".mp4"):
            file_path = os.path.join(destination_dir, file_name)
            os.remove(file_path)
            write_to_log(f"Fichier supprimé: {file_path}")

    # Étape 6: Copier les fichiers du répertoire /transcode contenant la date du jour dans destination_dir
    date_format = datetime.datetime.now().strftime("%Y-%m-%d")
    for file_name in os.listdir(transcode_dir):
        source_file = os.path.join(transcode_dir, file_name)
        destination_file = os.path.join(destination_dir, file_name)
        shutil.copyfile(source_file, destination_file)
        write_to_log(f"Fichier copié: {source_file} -> {destination_file}")

    # Scanner les fichiers dans la bibliothèque Plex
    plex.library.section('Télé Limoilou').update()

# Exécuter le script une fois sans délai
execute_script()
