import os
import subprocess
import sys
import json
import datetime
import locale
from pydub import AudioSegment
from pathlib import Path
import tempfile
import platform
import shutil

try:
    import config
except ImportError:
    print("Le fichier 'config.py' est manquant. Copiez 'config.py.sample' puis personnalisez-le.")
    sys.exit(1)

from utils import verifier_fichier_existe

# Fonctions utilitaires pour le transcodage

def choisir_codec(nom_codec: str, accel_intel: bool) -> str:
    """Retourne le codec ffmpeg à utiliser selon la configuration."""
    nom_codec = nom_codec.lower()
    if nom_codec == 'hevc':
        return 'hevc_qsv' if accel_intel else 'libx265'
    if nom_codec == 'h264':
        return 'h264_qsv' if accel_intel else 'libx264'
    return nom_codec

def obtenir_resolution(format_sortie: str) -> tuple:
    """Donne la largeur et la hauteur cibles selon le format indiqué."""
    if format_sortie == '720p':
        return 1280, 720
    return 1920, 1080

def obtenir_duree_ms(fichier: str) -> int:
    """Retourne la durée d'une vidéo en millisecondes."""
    commande = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', fichier
    ]
    sortie = subprocess.check_output(commande).decode('utf-8').strip()
    return int(float(sortie) * 1000)

def ajouter_chapitres(fichier_final: str, videos_source: list[str], titres: list[str]):
    """Insère des chapitres dans ``fichier_final`` sans perdre les métadonnées."""
    metadata_path = os.path.join(str(config.TRANSCODE_DIR), 'chapitres.txt')
    with open(metadata_path, 'w', encoding='utf-8') as f:
        f.write(';FFMETADATA1\n')
        start = 0
        for vid, titre in zip(videos_source, titres):
            duree = obtenir_duree_ms(vid)
            end = start + duree
            f.write('[CHAPTER]\n')
            f.write('TIMEBASE=1/1000\n')
            f.write(f'START={start}\n')
            f.write(f'END={end}\n')
            f.write(f'title={titre}\n')
            start = end
    temp_file = os.path.join(str(config.TRANSCODE_DIR), 'temp_chap.mp4')
    # On conserve les métadonnées existantes du fichier original et on importe
    # uniquement les chapitres générés dans ``metadata_path``.
    commande = [
        '-i', fichier_final, '-i', metadata_path,
        '-map_metadata', '0',
        '-map_chapters', '1',
        '-c', 'copy', '-y', temp_file
    ]
    run_ffmpeg_command(commande)
    os.remove(fichier_final)
    shutil.move(temp_file, fichier_final)
    os.remove(metadata_path)

python_path = sys.executable  # Donne le chemin du python actif

# Fonction pour détecter si le système d'exploitation est Linux
def is_linux():
    """Indique si le système courant est Linux."""
    return platform.system() == 'Linux'

# Fonction pour exécuter une commande ffmpeg via Docker ou directement
def run_ffmpeg_command(command):
    """Lance ``ffmpeg`` en utilisant Docker sous Linux ou localement ailleurs."""
    if is_linux():
        docker_command = [
    	    'docker', 'run', '--rm', 
            '--device=/dev/dri:/dev/dri',
            '-v', f'{os.path.abspath(os.getcwd())}:/config',
            '-v', '/mnt/medias_0:/mnt/medias_0',
            '-v', '/mnt/médias-voute:/mnt/médias-voute',
            '-v', f'{str(config.TRANSCODE_DIR)}:/tmp/transcode',
	    '--user', '0:0',  # Exécute le conteneur en tant que root
            'linuxserver/ffmpeg',
 #           '-hwaccel', 'qsv',
        ] + command
        print(f"Exécution de la commande via Docker : {' '.join(docker_command)}")
        subprocess.call(docker_command)
    else:
        win_command = [
            'ffmpeg ',
        ] + command    
        print(f"Exécution de la commande directement : {' '.join(win_command)}")
        subprocess.call(win_command)

# Fonction pour obtenir la résolution d'une vidéo
def get_video_resolution(video_path):
    """Retourne la largeur et la hauteur d'une vidéo en pixels."""
    video_path = str(Path(video_path))  # S'assurer que le chemin est portable
    command = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'csv=s=x:p=0',
        video_path
    ]
    output = subprocess.check_output(command).decode('utf-8').strip()
    width, height = map(int, output.split('x'))
    print(f"Résolution de la vidéo : {width}x{height}")
    return width, height

# Fonction pour normaliser l'audio
def normalize_audio_relative(input_file, output_file, target_db=-24):
    """Ajuste le volume d'un fichier audio pour viser ``target_db`` décibels."""
    audio = AudioSegment.from_file(input_file)
    loudness_difference = target_db - audio.dBFS
    normalized_audio = audio + loudness_difference
    normalized_audio.export(output_file, format="mp4")
    print(f"Audio normalisé et enregistré dans : {output_file}")

# Fonction pour transcoder une vidéo
def transcode_video(input_file, output_file, codec):
    """Transcode une vidéo en appliquant un redimensionnement et un codec."""
    width, height = get_video_resolution(input_file)
    
    command_sar = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=sample_aspect_ratio',
        '-of', 'csv=p=0',
        str(Path(input_file))
    ]
    sar = subprocess.check_output(command_sar).decode('utf-8').strip()

    new_width = width
    padded_width = width
    padded_height = height

    if sar != 'N/A' and sar != '1:1':
        try:
            sar_values = list(map(int, sar.split(':')))
            new_width = width * sar_values[0] // sar_values[1]
        except ValueError:
            print(f"Erreur lors du calcul du SAR pour la vidéo : {sar}")
            new_width = width

    target_width, target_height = obtenir_resolution(config.FORMAT_SORTIE)
    aspect_ratio = new_width / height

    if aspect_ratio > target_width / target_height:
        padded_width = target_width
        padded_height = int(target_width / aspect_ratio)
        padding_horizontal = 0
        padding_vertical = (target_height - padded_height) // 2
    else:
        padded_width = int(target_height * aspect_ratio)
        padded_height = target_height
        padding_horizontal = (target_width - padded_width) // 2
        padding_vertical = 0

    scale_filter = f'scale={padded_width}:{padded_height},setsar=1:1' if sar != 'N/A' and sar != '1:1' else f'scale={padded_width}:{padded_height}'

    temp_audio_file = os.path.join(os.path.dirname(output_file), 'audio_normalized.mp4')
    normalize_audio_relative(input_file, temp_audio_file)

    print("Début du transcodage vidéo")
    command = [
        '-threads', '1',
        '-i', input_file,
        '-i', temp_audio_file,
        '-map', '0:v',
        '-map', '1:a',
        '-c:v', codec,
    ]

 #   if codec.startswith('hevc'):
 #       command += ['-profile:v', 'main']

    bitrate = getattr(config, 'BITRATE_VIDEO', 1000)

    command += [
        '-b:v', f'{bitrate}k',
        '-maxrate', f'{bitrate}k',
        '-bufsize', f'{bitrate * 2}k',
        '-vf', f'{scale_filter},pad={target_width}:{target_height}:{padding_horizontal}:{padding_vertical}:black',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-ar', '48000',
        '-ac', '2',
        '-r', '24000/1001',
        '-fps_mode', 'cfr',  # Utiliser un fps constant
        '-y',
    ]

    if codec == 'hevc_qsv':
        command += ['-global_quality', '24']

    command.append(output_file)

    run_ffmpeg_command(command)

    try:
        os.remove(temp_audio_file)
    except FileNotFoundError:
        print(f"Le fichier temporaire {temp_audio_file} n'existe pas.")

# Fonction pour concaténer plusieurs vidéos
def concatenate_videos(video_files, output_file, metadata_title, metadata_description, chapters=None):
    """Assemble plusieurs vidéos en une seule et ajoute les chapitres."""
    # Utiliser un fichier temporaire pour concatener
    concat_file_path = os.path.join(str(config.TRANSCODE_DIR), 'concat.txt')

    existing_video_files = [video_file for video_file in video_files if os.path.exists(video_file)]

    with open(concat_file_path, 'w', encoding='utf-8') as f:
        for video_file in existing_video_files:
            f.write(f"file '{video_file}'\n")

    concat_command = [
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file_path,
        '-c:v', 'copy',
        '-c:a', 'copy',
        '-y',
        output_file
    ]
    
    print(f"Commande concaténation {concat_command}")

    run_ffmpeg_command(concat_command)
    print("Vidéos concaténées avec succès")


# Créer le fichier temp.mp4 dans le répertoire temporaire de transcode
    temp_output_file = os.path.join(str(config.TRANSCODE_DIR), 'temp.mp4')

    metadata_command = [
        '-i', output_file,
        '-metadata', f'title={metadata_title}',
        '-metadata', f'description={metadata_description}',
        '-metadata', 'language=fre',
        '-c', 'copy',
        '-y',
        temp_output_file
    ]

    run_ffmpeg_command(metadata_command)

    os.remove(output_file)
    shutil.move(temp_output_file, output_file)  # Utiliser shutil.move pour déplacer le fichier temp.mp4

    if chapters:
        ajouter_chapitres(output_file, existing_video_files, chapters)

    try:
        os.remove(concat_file_path)
    except FileNotFoundError:
        print(f"Le fichier temporaire {concat_file_path} n'existe pas.")

# Fonction pour mettre à jour le fichier emissions_def.json
def update_emissions_def(emissions, emission, rep_mode):
    """Met à jour le suivi des épisodes dans ``emissions_def.json``."""
    verifier_fichier_existe('emissions_def.json')
    with open('emissions_def.json', encoding='utf-8') as emissions_def_file:
        emissions_def = json.load(emissions_def_file)

    if rep_mode:
        series_to_increment = []
    else:
        series_to_increment = emission['a_incrementer']

    for series_name in series_to_increment:
        if 'series' in emissions_def:
            series_list = emissions_def['series']

            for series in series_list:
                if series['nom'] == series_name:
                    series['prochain'] = (series.get('prochain', 1) + 1) % (series.get('nb_episodes', 1) + 1)
                    if series['prochain'] == 0:
                        series['prochain'] = 1
                    break
            else:
                print(f"La série '{series_name}' n'a pas été trouvée dans emissions_def['series'].")
        else:
            print("Le fichier JSON ne contient pas de section 'series'.")

    with open('emissions_def.json', 'w', encoding='utf-8') as emissions_def_file:
        json.dump(emissions_def, emissions_def_file, indent=4, ensure_ascii=False)
    print("Mise à jour du fichier emissions_def.json terminée")

# Fonction principale
def main():
    """Transcode et assemble les segments listés dans ``listegeneration.json``."""
    input_dir = os.getcwd()

    # Utilisation du répertoire temporaire en utilisant tempfile pour garantir la portabilité
    output_dir = str(config.TRANSCODE_DIR)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    locale.setlocale(locale.LC_ALL, 'C')  # Utilisation de la locale C pour éviter des erreurs sous Windows


    codec = choisir_codec(config.CODEC_VIDEO, config.ACCEL_INTEL)
    rep_mode = False
    
    for arg in sys.argv[1:]:
        if arg.lower() == '-intel':
            codec = choisir_codec(config.CODEC_VIDEO, True)
        elif arg.lower() == '-standard':
            codec = choisir_codec(config.CODEC_VIDEO, False)
        elif arg.lower() == '-rep':
            rep_mode = True

    verifier_fichier_existe('listegeneration.json')
    verifier_fichier_existe('emissions_def.json')

    with open('listegeneration.json', encoding='utf-8') as f:
        data = json.load(f)
        emissions = data['emissions']

        for emission in emissions:
            if emission['genere']:
                continue

            titre_emission = emission['titre']
            date_diffusion = emission['date_diffusion']
            fichiers_concatenes = emission['fichiers_concatenes']
            description_emission = emission['description']

            date_diffusion_obj = datetime.datetime.strptime(date_diffusion, '%Y-%m-%d')
            nom_jour = date_diffusion_obj.strftime('%Y-%m-%d')

            emission_dir = output_dir
            output_file = os.path.join(emission_dir, f'{titre_emission} - {date_diffusion}.mp4')
            print(f"Début du traitement de l'émission '{titre_emission}'")

            for i, fichier in enumerate(fichiers_concatenes, start=1):
                input_file = os.path.join(input_dir, fichier)
                transcode_output = os.path.join(emission_dir, f'{i:02}.mp4')
                if os.path.exists(input_file):
                    transcode_video(input_file, transcode_output, codec)
                else:
                    print(f"Le fichier '{input_file}' n'existe pas. Passage au fichier suivant.")
                    continue

            video_files = [os.path.join(emission_dir, f'{i:02}.mp4') for i in range(1, len(fichiers_concatenes) + 1)]
            video_files = [video_file for video_file in video_files if os.path.exists(video_file)]

            chapitres = [os.path.splitext(os.path.basename(f))[0] for f in fichiers_concatenes]
            concatenate_videos(video_files, output_file, f'Émission du {nom_jour}', description_emission, chapitres)

            for video_file in video_files:
                os.remove(video_file)

            emission['genere'] = True
            
            update_emissions_def(emissions, emission, rep_mode)
            
            break  # Sortir de la boucle après avoir traité la première émission
         
    with open('listegeneration.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

if __name__ == '__main__':
    main()
