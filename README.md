# Scripts Télé Limoilou

Ce dépôt regroupe les scripts utilisés pour générer et transcoder le contenu de Télé Limoilou. Ils communiquent avec un serveur Plex, utilisent plusieurs APIs d'IA pour produire des messages et s'appuient sur `ffmpeg` pour le traitement vidéo.

## Prérequis

- Python 3.9 ou plus récent
- `ffmpeg` installé localement ou accessible via Docker
- Les dépendances listées dans `requirements.txt`

Installez-les avec :

```bash
pip install -r requirements.txt
```

## Variables d'environnement

Avant d'exécuter les scripts, définissez au minimum :

```bash
export PLEX_BASEURL="http://adresse-de-votre-plex:32400"
export PLEX_TOKEN="votre-token-plex"
export ANTHROPIC_API_KEY="cle-anthropic"
export OPENAI_API_KEY="cle-openai"
export GEMINI_API_KEY="cle-gemini"
```

Les chemins de sortie peuvent être modifiés dans `config.py`.
Copiez d'abord `modeles/config.py.sample` vers `config.py` puis ajustez les valeurs.

### Paramètres de transcodage

Le fichier `config.py` contient plusieurs options pour régler la qualité de sortie :

- `FORMAT_SORTIE` choisit la résolution cible (`"720p"` ou `"1080p"`).
- `CODEC_VIDEO` définit le codec (`"hevc"` pour H.265 ou `"h264"` pour H.264).
- `ACCEL_INTEL` active l'encodage matériel Intel s'il est disponible.

- `BITRATE_VIDEO` fixe le débit maximal de la vidéo (en kb/s). Une valeur
  plus élevée améliore la qualité mais augmente la taille du fichier final.

Lorsqu'`CODEC_VIDEO` est réglé sur `"hevc"`, le profil *Main* (8 bits) est appliqué
par défaut pour garantir la compatibilité avec la plupart des lecteurs, même si
la source est encodée en 10 bits.

Ces options permettent de changer facilement la taille et le codec de la vidéo finale.

## Description des scripts

- **scanneurvid.py** : scanne les répertoires ou Plex pour mettre à jour `bd_videos.json` et `emissions_def.json`.
- **generer.py** : génère `listegeneration.json` à partir des définitions d'émissions et des épisodes disponibles.
- **genmessages.py** : produit des messages et des descriptions d'images via les APIs Anthropic, OpenAI ou Gemini puis les sauvegarde dans `messages.json`.
- **genvidmessage.py** : crée une vidéo à partir d'un message en générant l'audio et l'image correspondante.
- **transcode.py** : assemble et encode les segments vidéo listés dans `listegeneration.json` et met à jour `emissions_def.json`.
- **concierge.py** : orchestrateur principal qui exécute les étapes précédentes et gère la mise à jour de la bibliothèque Plex.

## Fichiers de données

Les versions utilisables de ces fichiers ne sont pas suivies par Git. Le dépôt
contient des exemples avec l'extension `.sample` :

- `emissions_def.json.sample`
- `bd_videos.json.sample`
- `listegeneration.json.sample`
- `messages.json.sample`

Copiez chaque fichier exemple sans l'extension `.sample` pour créer vos propres
données :

```bash
cp emissions_def.json.sample emissions_def.json
cp bd_videos.json.sample bd_videos.json
cp listegeneration.json.sample listegeneration.json
cp messages.json.sample messages.json
```

Faites de même pour `config.py` en partant de `config.py.sample`.

## Interface CLI (Nouveau!)

**Télé Limoilou v2** inclut maintenant une interface de gestion interactive en ligne de commande!

### Lancement du CLI

```bash
python cli.py
```

L'interface CLI offre :

- **Menu interactif** avec navigation au clavier
- **Affichage élégant** avec couleurs, tableaux et panneaux
- **Gestion facilitée** de toutes les opérations
- **Éditeur de liste** pour modifier la planification
- **Statistiques** en temps réel du système
- **Feedback visuel** pour chaque opération

### Fonctionnalités disponibles

1. Scanner les vidéos
2. Générer la liste d'émissions
3. Générer les messages IA
4. Régénérer l'émission du jour (complet: message + transcodage + copie + Plex)
5. Éditer la liste de génération
6. Afficher le statut et statistiques
7. Quitter

Pour plus de détails, consultez [CLI_README.md](CLI_README.md).

## Exemple d'exécution

### Avec l'interface CLI (recommandé)

```bash
python cli.py
```

### Avec les scripts individuels

Pour lancer la chaîne complète de génération :

```bash
python concierge.py
```

Chaque script peut aussi être exécuté séparément selon les besoins.

