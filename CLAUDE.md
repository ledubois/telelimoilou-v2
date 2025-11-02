# CLAUDE.md

Ce fichier fournit des directives à Claude Code (claude.ai/code) lors du travail avec le code dans ce dépôt.

## Vue d'ensemble du projet

**Télé Limoilou** est un système de génération et de transcodage de contenu vidéo pour une chaîne télévisée personnalisée. Le projet s'intègre avec Plex, utilise plusieurs APIs d'IA (Anthropic, OpenAI, Gemini) pour générer des messages, et s'appuie sur `ffmpeg` pour le traitement vidéo.

## Installation et configuration

### Installation des dépendances

```bash
pip install -r requirements.txt
```

### Configuration initiale

1. Copier les fichiers d'exemple et les personnaliser :

```bash
cp modeles/config.py.sample config.py
cp modeles/emissions_def.json.sample emissions_def.json
cp modeles/bd_videos.json.sample bd_videos.json
cp modeles/listegeneration.json.sample listegeneration.json
cp modeles/messages.json.sample messages.json
```

2. Définir les variables d'environnement nécessaires dans `.env` ou directement :

```bash
export PLEX_BASEURL="http://adresse-de-votre-plex:32400"
export PLEX_TOKEN="votre-token-plex"
export ANTHROPIC_API_KEY="cle-anthropic"
export OPENAI_API_KEY="cle-openai"
export GEMINI_API_KEY="cle-gemini"
```

### Prérequis système

- Python 3.9 ou plus récent
- `ffmpeg` installé et accessible dans le PATH
- `ffprobe` (généralement fourni avec ffmpeg)

## Architecture du projet

### Scripts principaux (flux de travail)

L'orchestration complète se fait via **concierge.py** qui exécute les étapes suivantes :

1. **scanneurvid.py** : scanne Plex ou des répertoires locaux pour mettre à jour :
   - `bd_videos.json` : base de données des vidéos disponibles
   - `emissions_def.json` : définitions des émissions

2. **generer.py** : génère `listegeneration.json` qui contient la liste des épisodes à créer, en croisant les définitions d'émissions avec les vidéos disponibles

3. **genmessages.py** : utilise les APIs d'IA pour générer :
   - Des messages textuels
   - Des descriptions d'images
   - Sauvegarde tout dans `messages.json`

4. **genvidmessage.py** : crée des vidéos de messages en :
   - Générant l'audio à partir du texte
   - Créant l'image correspondante
   - Assemblant le tout en vidéo

5. **transcode.py** : assemble et encode les segments vidéo listés dans `listegeneration.json`, puis met à jour `emissions_def.json` avec les épisodes générés

### Fichiers de configuration

- **config.py** : configuration centrale du projet incluant :
  - Clés API pour les services d'IA
  - Paramètres de connexion Plex
  - Chemins de sortie (mapping Linux/Windows)
  - Paramètres de transcodage (résolution, codec, bitrate, accélération matérielle)

### Utilitaires

- **utils.py** : fonctions utilitaires partagées entre les scripts

### Paramètres de transcodage importants

Dans `config.py` :
- `FORMAT_SORTIE` : résolution cible (`"720p"` ou `"1080p"`)
- `CODEC_VIDEO` : codec d'encodage (`"hevc"` pour H.265 ou `"h264"` pour H.264)
- `ACCEL_INTEL` : active l'encodage matériel Intel QuickSync (booléen)
- `BITRATE_VIDEO` : débit maximal en kb/s

Le système détecte automatiquement l'OS (Linux/Windows) et adapte les chemins via `PATH_MAPPINGS`.

## Commandes de développement

### Exécution complète de la chaîne

```bash
python concierge.py
```

### Exécution des scripts individuels

```bash
# Scanner les vidéos
python scanneurvid.py

# Générer la liste de génération
python generer.py

# Générer les messages IA
python genmessages.py

# Créer une vidéo de message
python genvidmessage.py

# Transcoder les vidéos
python transcode.py
```

## Conventions de code

### Langue
Tout le code, les commentaires et la documentation sont en français canadien.

### Style
- Noms de variables et fonctions : snake_case
- Les chemins de fichiers utilisent `pathlib.Path` plutôt que des chaînes
- Gestion d'erreurs : les scripts vérifient la présence de `config.py` au démarrage et quittent proprement si absent

### Fichiers de données
Les fichiers `.json` et `config.py` ne sont **pas versionnés** (dans `.gitignore`). Seuls les fichiers `.sample` sont suivis dans Git pour servir de modèles.
