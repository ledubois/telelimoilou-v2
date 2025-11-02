"""Génération automatisée de vidéos à partir de messages.

Ce script lit ``messages.json`` pour créer une vidéo comportant une image
et un enregistrement audio pour chaque message non encore généré.
"""
import json
import os
import shutil
from pathlib import Path
import openai
import requests
import argparse
import time
from datetime import datetime
import mimetypes
import platform
import tempfile
import subprocess
import base64
import sys
try:
    import config
except ImportError:
    print("Le fichier 'config.py' est manquant. Copiez 'config.py.sample' puis personnalisez-le.")
    sys.exit(1)

from utils import verifier_fichier_existe

# Détecter le système d'exploitation
os_name = config.OS_NAME

python_path = sys.executable  # Donne le chemin du python actif


# Chemins importants
messages_file_path = Path.cwd() / "messages.json"
temp_dir = config.GENMESSAGE_DIR
output_dir = config.MESSAGE_OUTPUT_DIR
archive_dir = config.MESSAGE_ARCHIVE_DIR
log_file_path = Path.cwd() / "logmessages.txt"

# Supprimer le répertoire temporaire s'il existe
if temp_dir.exists():
    shutil.rmtree(temp_dir)

# Créer le répertoire temporaire
temp_dir.mkdir(parents=True, exist_ok=True)

# Définir les arguments de ligne de commande
parser = argparse.ArgumentParser()
parser.add_argument("--iterations", type=int, default=1, help="Nombre d'itérations (vidéos à générer)")
args = parser.parse_args()

# Charger les messages
verifier_fichier_existe(str(messages_file_path))
with open(messages_file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

# Fonctions utilitaires

def generate_image_from_prompt(client, prompt_text, output_path, max_attempts=3):
    """Génère une image avec GPT-Image-1 et la sauvegarde."""
    attempts = 0
    while attempts < max_attempts:
        try:
            print(f"Tentative de génération d'image ({attempts + 1}/{max_attempts})...")
            response = client.images.generate(
                model="gpt-image-1",
                prompt=prompt_text,
                size="1536x1024",
                quality="auto"
            )
            image_base64 = response.data[0].b64_json
            image_bytes = base64.b64decode(image_base64)
            with open(output_path, 'wb') as file:
                file.write(image_bytes)
            print(f"Image générée et sauvegardée : {output_path}")
            return True
        except Exception as e:
            attempts += 1
            print(f"Erreur lors de la génération de l'image : {e}")
            if attempts < max_attempts:
                print("Nouvelle tentative dans 5 minutes...")
                time.sleep(300)
            else:
                print("Échec après plusieurs tentatives.")
                return False

# Traitement principal
stop_processing = False
for category, messages in data['Messages'].items():
    if stop_processing:
        break
    for i in range(args.iterations):
        if stop_processing:
            break
        for message in messages:
            if isinstance(message, dict) and not message['genere']:
                print(f"Génération de la vidéo pour le message {message['id']}...")

                client = openai.OpenAI()
                speech_file_path = temp_dir / f"message_{message['id']}.mp3"
                audio_generated = False
                audio_attempts = 0

                # Génération de l'audio
                while not audio_generated and audio_attempts < 3:
                    try:
                        response = client.audio.speech.create(
                            model="gpt-4o-mini-tts",
                            voice="nova",
                            input=message['texteMessage'],
                            instructions="Parlez sur un ton dynamique, mais posé, en articulant clairement.",
                        )
                        with open(speech_file_path, 'wb') as audio_file:
                            audio_file.write(response.content)
                        print("Fichier audio généré.")
                        audio_generated = True
                    except Exception as e:
                        audio_attempts += 1
                        error_message = f"Erreur audio pour message {message['id']} (tentative {audio_attempts}) : {str(e)}"
                        print(error_message)
                        with open(log_file_path, 'a', encoding='utf-8') as log_file:
                            log_file.write(error_message + "\n")
                        if audio_attempts < 3:
                            print("Nouvelle tentative dans 5 minutes...")
                            time.sleep(300)

                if not audio_generated:
                    print(f"Échec de génération de l'audio pour {message['id']} après 3 tentatives. Passage au message suivant.")
                    message['genere'] = True
                    continue

                # Génération ou téléchargement de l'image
                image_generated = False
                image_description = message['descriptionImage']
                image_file_path = temp_dir / f"image_{message['id']}.jpg"

                if image_description.startswith("http"):
                    try:
                        response = requests.get(image_description)
                        content_type = response.headers['Content-Type']
                        extension = mimetypes.guess_extension(content_type)
                        if extension:
                            image_file_path = temp_dir / f"image_{message['id']}{extension}"
                        with open(image_file_path, 'wb') as file:
                            file.write(response.content)
                        print(f"Image téléchargée depuis l'URL avec extension {extension}.")
                        image_generated = True
                    except Exception as e:
                        error_message = f"Erreur téléchargement image URL pour {message['id']}: {str(e)}"
                        print(error_message)
                        with open(log_file_path, 'a', encoding='utf-8') as log_file:
                            log_file.write(error_message + "\n")
                else:
                    image_generated = generate_image_from_prompt(
                        client=client,
                        prompt_text=image_description,
                        output_path=image_file_path
                    )

                if not image_generated:
                    print(f"Échec image pour {message['id']}. Passage au message suivant.")
                    message['genere'] = True
                    continue

                print(image_description)

                # Définir la durée de l'audio
                audio_duration = float(subprocess.check_output(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", str(speech_file_path)]
                ).strip())

                # Déplacer les anciens fichiers vidéos vers l'archive
                for filename in os.listdir(output_dir):
                    file_path = os.path.join(output_dir, filename)
                    if os.path.isfile(file_path):
                        creation_time = os.path.getctime(file_path)
                        creation_date = datetime.fromtimestamp(creation_time)
                        date_string = creation_date.strftime("%Y-%m-%d")
                        new_filename = f"{date_string}_{filename}"
                        archive_path = os.path.join(archive_dir, new_filename)
                        shutil.move(file_path, archive_path)
                        print(f"Fichier {filename} archivé vers {archive_path}.")

                # Création de la vidéo
                silence_file_path = str(Path.cwd() / "silence.mp3")
                output_path = output_dir / "message.mp4"
                ffmpeg_command = [
                    "ffmpeg",
                    "-threads", "1",
                    "-loop", "1",
                    "-i", str(image_file_path),
                    "-i", str(speech_file_path),
                    "-i", silence_file_path,
                    "-i", silence_file_path,
                    "-filter_complex",
                    f"[1]adelay=2000|2000[a1];[2]adelay=0|0[a2];[3]adelay={int(audio_duration * 1000) + 2000}|{int(audio_duration * 1000) + 2000}[a3];[a2][a1][a3]amix=inputs=3[audio]",
                    "-map", "0:v",
                    "-map", "[audio]",
                    "-c:v", "libx264",
                    "-t", str(audio_duration + 4),
                    "-pix_fmt", "yuv420p",
                    "-vf", "scale=1280:720",
                    "-r", "24",
                    "-shortest",
                    str(output_path)
                ]
                subprocess.run(ffmpeg_command, check=True)
                print("Vidéo générée.")

                # Archiver les images générées
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    if os.path.isfile(file_path) and filename.lower().endswith('.jpg'):
                        creation_time = os.path.getctime(file_path)
                        creation_date = datetime.fromtimestamp(creation_time)
                        date_string = creation_date.strftime("%Y-%m-%d")
                        new_filename = f"{date_string}_{filename}"
                        archive_path = os.path.join(archive_dir, new_filename)
                        shutil.move(file_path, archive_path)
                        print(f"Fichier {filename} archivé.")

                message['genere'] = True
                stop_processing = True
                break

# Sauvegarder les changements
with open(messages_file_path, 'w', encoding='utf-8') as file:
    json.dump(data, file, ensure_ascii=False, indent=2)
print("Traitement terminé.")
