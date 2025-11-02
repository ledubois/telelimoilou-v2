# Interface CLI de Télé Limoilou

Interface de gestion en ligne de commande pour Télé Limoilou v2.

## Installation

1. Installer les dépendances :

```bash
pip install -r requirements.txt
```

2. Configurer le fichier `config.py` (copier depuis `config.py.sample`)

## Utilisation

Lancer l'interface interactive :

```bash
python cli.py
```

ou directement :

```bash
./cli.py
```

## Fonctionnalités

### 1. Scanner les vidéos

Scanne les bibliothèques Plex et les répertoires locaux pour mettre à jour :
- `bd_videos.json` : base de données des vidéos disponibles
- `emissions_def.json` : mise à jour du nombre d'épisodes par série

### 2. Générer la liste d'émissions

Génère `listegeneration.json` contenant la planification des émissions à créer.

**Paramètres demandés** :
- Nombre de jours à générer
- Date de départ (format AAAA-MM-JJ)

### 3. Générer les messages IA

Lance le processus interactif de génération de messages avec les APIs d'IA (Anthropic, OpenAI ou Gemini).

Le script vous guidera à travers :
- Le choix de l'API
- La saisie du sujet
- Le nombre de messages à générer
- L'édition des prompts
- La génération des textes et descriptions d'images

### 4. Régénérer l'émission du jour

Processus complet de régénération en 4 étapes :

1. **Création du message vidéo** : génère la vidéo d'introduction
2. **Transcodage** : assemble et transcode les segments de l'émission
3. **Copie vers Plex** : déplace les fichiers vers le répertoire Plex
4. **Rafraîchissement Plex** : met à jour la bibliothèque Plex

### 5. Éditer la liste de génération

Interface interactive pour gérer `listegeneration.json` :

- **Voir la liste** : affiche toutes les émissions planifiées
- **Marquer comme générée** : marque une émission comme complétée
- **Marquer comme non générée** : réinitialise le statut d'une émission
- **Supprimer** : retire une émission de la liste

### 6. Afficher le statut et statistiques

Tableau de bord complet du système affichant :

**Séries disponibles** :
- Nom de chaque série
- Nombre d'épisodes disponibles
- Prochain épisode à diffuser (pour les séries séquentielles)

**Liste de génération** :
- Nombre d'émissions générées vs à générer
- Détail des prochaines émissions planifiées

**Messages IA** :
- Statistiques par sujet
- Nombre de messages générés vs non générés

**Dernière activité** :
- Dernière entrée du fichier log

## Interface

L'interface utilise :
- **Rich** : affichage élégant avec couleurs, tableaux et panneaux
- **Questionary** : menus interactifs avec navigation au clavier

### Navigation

- Utilisez les **flèches haut/bas** pour naviguer dans les menus
- **Entrée** pour sélectionner
- **Ctrl+C** pour quitter à tout moment

## Fichiers importants

- `cli.py` : interface de gestion principale
- `bd_videos.json` : base de données des vidéos
- `emissions_def.json` : définitions des émissions et séries
- `listegeneration.json` : planification des émissions
- `messages.json` : messages IA générés
- `log.txt` : historique des opérations

## Avantages du CLI

- **Interface intuitive** : navigation facile avec les flèches
- **Feedback visuel** : barres de progression, couleurs, tableaux
- **Gestion d'erreurs** : messages clairs en cas de problème
- **Flexibilité** : exécution des opérations individuellement ou en séquence
- **Édition facilitée** : modification de la liste sans éditer le JSON manuellement
- **Statistiques** : vue d'ensemble du système en un coup d'œil

## Dépannage

### Le CLI ne démarre pas

Vérifiez que toutes les dépendances sont installées :

```bash
pip install -r requirements.txt
```

### Erreur "config.py manquant"

Copiez et configurez le fichier de configuration :

```bash
cp modeles/config.py.sample config.py
# Éditez config.py avec vos paramètres
```

### Erreur "Fichier JSON manquant"

Assurez-vous que les fichiers JSON de base existent :

```bash
cp modeles/bd_videos.json.sample bd_videos.json
cp modeles/emissions_def.json.sample emissions_def.json
cp modeles/listegeneration.json.sample listegeneration.json
cp modeles/messages.json.sample messages.json
```

## Développement futur

Fonctionnalités potentielles :
- Mode batch pour automatisation
- Export des statistiques en CSV
- Notifications lors de la fin des opérations
- Intégration avec un système de tâches planifiées
- Gestion avancée des messages (filtrage, recherche)
