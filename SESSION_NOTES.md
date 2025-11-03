# Notes de sessions de développement - Télé Limoilou v2

## Session du 2 novembre 2024 - Création de l'interface CLI

### 🎯 Objectif de la session
Créer une interface de gestion interactive en ligne de commande pour faciliter l'utilisation de Télé Limoilou v2 sans casser la version en production.

---

### 🚀 Réalisations

#### 1. Création du nouveau dépôt GitHub
- ✅ Nouveau dépôt créé : `telelimoilou-v2`
- ✅ URL : https://github.com/ledubois/telelimoilou-v2
- ✅ Copie complète du code sans historique Git
- ✅ Premier commit et push réussi

#### 2. Développement de l'interface CLI interactive
- ✅ Script `cli.py` complet (740 lignes)
- ✅ Bibliothèques utilisées : Rich + Questionary
- ✅ Dépendances ajoutées au `requirements.txt`

**Fonctionnalités implémentées** :
1. **Scanner les vidéos** - Exécute scanneurvid.py avec affichage en temps réel
2. **Générer la liste d'émissions** - Demande interactivement le nombre de jours et la date
3. **Générer les messages IA** - Lance le processus interactif de genmessages.py
4. **Régénérer l'émission du jour** - Processus complet en 4 étapes :
   - Création du message vidéo
   - Transcodage
   - Copie vers Plex
   - Rafraîchissement de la bibliothèque
5. **Éditer la liste de génération** - Interface interactive pour :
   - Voir toutes les émissions
   - Marquer comme générée/non générée
   - Supprimer des émissions
6. **Afficher les statistiques** - Tableau de bord complet :
   - Séries disponibles avec nombre d'épisodes
   - Prochains épisodes séquentiels
   - État des émissions (générées vs à générer)
   - Messages IA par sujet
   - Dernière activité du système
7. **Quitter** - Sortie propre de l'application

#### 3. Documentation
- ✅ `CLI_README.md` créé (guide complet d'utilisation)
- ✅ `README.md` mis à jour avec section CLI
- ✅ Documentation des fonctionnalités et exemples

#### 4. Déploiement sur le serveur de production
- ✅ Serveur : 192.168.68.4 (user: ledubois)
- ✅ Répertoire : `/home/ledubois/apps/telelimoilou-v2`
- ✅ Clonage du dépôt depuis GitHub
- ✅ Création de l'environnement virtuel Python
- ✅ Installation de toutes les dépendances
- ✅ Copie des fichiers de configuration depuis `/opt/telelimoilou`
- ✅ Script wrapper `run_cli.sh` créé
- ✅ **CLI testé et fonctionnel !**

---

### 📂 Structure finale du projet

```
/home/ledubois/apps/telelimoilou-v2/
├── cli.py                   # Interface CLI principale ⭐ NOUVEAU
├── run_cli.sh              # Script de lancement ⭐ NOUVEAU
├── CLI_README.md           # Documentation CLI ⭐ NOUVEAU
├── SESSION_NOTES.md        # Ce fichier ⭐ NOUVEAU
├── venv/                    # Environnement virtuel
│   └── [dépendances Python]
├── config.py               # Configuration (copié depuis v1)
├── bd_videos.json          # Base de données vidéos
├── emissions_def.json      # Définitions émissions
├── listegeneration.json    # Liste de génération
├── messages.json           # Messages IA
├── concierge.py            # Scripts existants
├── generer.py
├── genmessages.py
├── genvidmessage.py
├── scanneurvid.py
├── transcode.py
└── utils.py
```

---

### 🛠️ Problèmes résolus

#### Problème 1 : Mot de passe sudo via SSH
**Symptôme** : Impossible de créer le répertoire dans `/opt/`
**Solution** : Utilisation de `/home/ledubois/apps/` à la place

#### Problème 2 : Création du venv au mauvais endroit
**Symptôme** : Le venv se créait dans `/home/ledubois/` au lieu du projet
**Solution** : Utilisation du chemin absolu : `python3 -m venv /home/ledubois/apps/telelimoilou-v2/venv`

#### Problème 3 : Module `dotenv` manquant
**Symptôme** : `ModuleNotFoundError: No module named 'dotenv'`
**Solution** : Installation de `python-dotenv` dans le venv

#### Problème 4 : Python ne trouve pas config.py
**Symptôme** : "Le fichier 'config.py' est manquant"
**Solution** : Script wrapper qui change de répertoire avant d'exécuter le CLI

---

### 🎯 Utilisation du CLI

#### Méthode 1 : Via SSH interactif (Recommandé)
```bash
ssh ledubois@192.168.68.4
/home/ledubois/apps/telelimoilou-v2/run_cli.sh
```

#### Méthode 2 : En une ligne
```bash
ssh -t ledubois@192.168.68.4 "/home/ledubois/apps/telelimoilou-v2/run_cli.sh"
```

#### Méthode 3 : Créer un alias (optionnel)
Ajouter dans `~/.bashrc` ou `~/.zshrc` :
```bash
alias tvl2='ssh -t ledubois@192.168.68.4 "/home/ledubois/apps/telelimoilou-v2/run_cli.sh"'
```

---

### 📦 Dépendances installées

```
plexapi
openai
anthropic
google-generativeai
pydub
requests
python-magic
rich                  # ⭐ NOUVEAU - Affichage élégant
questionary          # ⭐ NOUVEAU - Menus interactifs
python-dotenv        # ⭐ NOUVEAU - Variables d'environnement
```

---

### ✨ Points forts de l'interface CLI

- **Interface moderne** avec couleurs et tableaux Rich
- **Navigation intuitive** avec menus interactifs Questionary
- **Feedback en temps réel** pour chaque opération
- **Éditeur intégré** pour la liste de génération
- **Statistiques détaillées** du système
- **Aucune modification** des scripts existants (approche wrapper)
- **Compatible** avec l'utilisation actuelle des scripts
- **Gestion d'erreurs** améliorée et messages clairs

---

### 📝 Notes techniques

#### Architecture choisie
- **Approche par wrapper** : Le CLI appelle les scripts existants via `subprocess`
- **Avantages** :
  - Pas de refactoring des scripts existants nécessaire
  - Compatible avec l'usage actuel des scripts
  - Développement rapide
  - Moins de risques de casser la production

#### Fichiers non versionnés
Le fichier `requirements.txt` est dans `.gitignore` (à cause de la règle `*.txt`), mais le serveur de production a déjà toutes les dépendances installées.

#### Configuration
Les fichiers de configuration ont été copiés depuis `/opt/telelimoilou` :
- `config.py`
- `bd_videos.json`
- `emissions_def.json`
- `listegeneration.json`
- `messages.json`

---

### 🔄 Prochaines étapes possibles

#### Améliorations suggérées pour le futur
1. **Mode batch** pour automatisation sans interaction
2. **Export des statistiques** en CSV
3. **Notifications** lors de la fin des opérations longues
4. **Gestion avancée des messages** (filtrage, recherche)
5. **Logs améliorés** avec rotation automatique
6. **Barres de progression** plus détaillées pour le transcodage
7. **Validation** des fichiers de configuration au démarrage
8. **Tests unitaires** pour le CLI

#### Considérations
- Évaluer si on veut versionner `requirements.txt` (modifier `.gitignore`)
- Possibilité de créer des raccourcis système pour faciliter l'accès
- Documentation vidéo de démonstration pour les utilisateurs

---

### 🎊 Conclusion

Session très productive ! L'interface CLI est maintenant opérationnelle et offre une expérience utilisateur moderne pour gérer Télé Limoilou v2. Le système est déployé sur le serveur de production et prêt à être utilisé sans risque pour la version v1 actuelle.

**Statut** : ✅ Production Ready
**Environnement** : Serveur 192.168.68.4
**Version** : v2.0.0 (première version avec CLI)
**Date** : 2 novembre 2024

---

## Historique des commits

### Commit 1 - Version initiale
```
Version initiale de Télé Limoilou v2

Point de départ pour la refonte majeure du système de génération
et de transcodage de contenu vidéo.
```

### Commit 2 - Ajout du CLI
```
Ajout de l'interface CLI interactive pour Télé Limoilou v2

Nouvelle fonctionnalité majeure : interface de gestion en ligne de commande
avec menu interactif, affichage Rich et navigation au clavier.

Fichiers ajoutés :
- cli.py : interface principale
- CLI_README.md : documentation détaillée

Fichiers modifiés :
- README.md : ajout de la section CLI
```
