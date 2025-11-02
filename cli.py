#!/usr/bin/env python3
"""
Interface de gestion en ligne de commande pour Télé Limoilou.

Ce module fournit une interface interactive pour gérer toutes les opérations
de génération et de transcodage de contenu vidéo pour la chaîne Télé Limoilou.
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

import questionary
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich import box
from rich.text import Text

try:
    import config
except ImportError:
    print("Le fichier 'config.py' est manquant. Copiez 'config.py.sample' puis personnalisez-le.")
    sys.exit(1)

from plexapi.server import PlexServer

# Configuration
console = Console()
python_path = sys.executable
script_dir = Path(__file__).parent.resolve()


def afficher_banniere():
    """Affiche la bannière de l'application."""
    banniere = Text()
    banniere.append("🎬 Télé Limoilou", style="bold cyan")
    banniere.append(" - Interface de gestion\n", style="bold white")

    panel = Panel(
        banniere,
        box=box.DOUBLE,
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(panel)


def executer_script(script_name, args=None, description="Exécution du script"):
    """
    Exécute un script Python et affiche sa sortie avec Rich.

    Args:
        script_name: Nom du script à exécuter
        args: Liste d'arguments à passer au script
        description: Description de l'opération

    Returns:
        bool: True si succès, False sinon
    """
    script_path = script_dir / script_name
    cmd = [python_path, str(script_path)]

    if args:
        cmd.extend(args)

    console.print(f"\n[bold cyan]→[/bold cyan] {description}...")
    console.print(f"[dim]Commande: {' '.join(cmd)}[/dim]\n")

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Afficher la sortie en temps réel
        for line in process.stdout:
            console.print(f"  [dim]{line.rstrip()}[/dim]")

        process.wait()

        if process.returncode == 0:
            console.print(f"\n[bold green]✓[/bold green] {description} terminé avec succès\n")
            return True
        else:
            console.print(f"\n[bold red]✗[/bold red] {description} a échoué (code: {process.returncode})\n")
            return False

    except Exception as e:
        console.print(f"\n[bold red]✗ Erreur:[/bold red] {str(e)}\n")
        return False


def scanner_videos():
    """Scan les vidéos Plex et locales."""
    console.print("\n[bold yellow]Scanner les vidéos[/bold yellow]")
    console.rule(style="yellow")

    return executer_script(
        "scanneurvid.py",
        description="Scan des vidéos Plex et locales"
    )


def generer_liste_emissions():
    """Génère la liste des émissions à produire."""
    console.print("\n[bold yellow]Générer la liste d'émissions[/bold yellow]")
    console.rule(style="yellow")

    # Demander le nombre de jours
    nb_jours = questionary.text(
        "Nombre de jours à générer:",
        default="1",
        validate=lambda x: x.isdigit() and int(x) > 0
    ).ask()

    if not nb_jours:
        console.print("[yellow]Opération annulée[/yellow]")
        return False

    # Demander la date de départ
    date_defaut = datetime.now().strftime("%Y-%m-%d")
    date_debut = questionary.text(
        "Date de départ (AAAA-MM-JJ):",
        default=date_defaut,
        validate=lambda x: len(x) == 10 and x[4] == '-' and x[7] == '-'
    ).ask()

    if not date_debut:
        console.print("[yellow]Opération annulée[/yellow]")
        return False

    return executer_script(
        "generer.py",
        args=[nb_jours, date_debut],
        description=f"Génération de {nb_jours} jour(s) à partir du {date_debut}"
    )


def generer_messages_ia():
    """Génère les messages IA avec l'API choisie."""
    console.print("\n[bold yellow]Générer les messages IA[/bold yellow]")
    console.rule(style="yellow")

    console.print("\n[bold]Ce script est interactif et vous guidera à travers le processus.[/bold]\n")

    return executer_script(
        "genmessages.py",
        description="Génération des messages IA"
    )


def regenerer_emission_jour():
    """Régénère l'émission du jour complète."""
    console.print("\n[bold yellow]Régénérer l'émission du jour[/bold yellow]")
    console.rule(style="yellow")

    confirmation = questionary.confirm(
        "Voulez-vous régénérer l'émission du jour? (message + transcodage + copie + rafraîchissement Plex)",
        default=False
    ).ask()

    if not confirmation:
        console.print("[yellow]Opération annulée[/yellow]")
        return False

    # Étape 1: Créer le message vidéo
    console.print("\n[bold cyan]Étape 1/4:[/bold cyan] Création du message vidéo")
    if not executer_script("genvidmessage.py", description="Création du message vidéo"):
        console.print("[bold red]Échec de la création du message vidéo[/bold red]")
        return False

    # Étape 2: Transcoder
    console.print("\n[bold cyan]Étape 2/4:[/bold cyan] Transcodage de l'émission")
    if not executer_script("transcode.py", description="Transcodage de l'émission"):
        console.print("[bold red]Échec du transcodage[/bold red]")
        return False

    # Étape 3: Copier vers Plex
    console.print("\n[bold cyan]Étape 3/4:[/bold cyan] Copie vers le répertoire Plex")
    try:
        destination_dir = Path(config.TVLIMOILOU_DIR)
        transcode_dir = Path(config.TRANSCODE_DIR)

        # Supprimer les anciens fichiers MP4
        for file_name in os.listdir(destination_dir):
            if file_name.endswith(".mp4"):
                file_path = destination_dir / file_name
                os.remove(file_path)
                console.print(f"  [dim]Fichier supprimé: {file_name}[/dim]")

        # Copier les nouveaux fichiers
        date_format = datetime.now().strftime("%Y-%m-%d")
        for file_name in os.listdir(transcode_dir):
            if file_name.endswith(".mp4"):
                source_file = transcode_dir / file_name
                destination_file = destination_dir / file_name
                shutil.copyfile(source_file, destination_file)
                console.print(f"  [dim]Fichier copié: {file_name}[/dim]")

        console.print("[bold green]✓[/bold green] Copie terminée\n")

    except Exception as e:
        console.print(f"[bold red]✗ Erreur lors de la copie:[/bold red] {str(e)}\n")
        return False

    # Étape 4: Rafraîchir Plex
    console.print("\n[bold cyan]Étape 4/4:[/bold cyan] Rafraîchissement de la bibliothèque Plex")
    try:
        plex = PlexServer(config.PLEX_BASEURL, config.PLEX_TOKEN)
        plex.library.section('Télé Limoilou').update()
        console.print("[bold green]✓[/bold green] Bibliothèque Plex rafraîchie\n")
    except Exception as e:
        console.print(f"[bold red]✗ Erreur lors du rafraîchissement Plex:[/bold red] {str(e)}\n")
        return False

    console.print("\n[bold green]🎉 Régénération complète terminée avec succès![/bold green]\n")
    return True


def afficher_statistiques():
    """Affiche les statistiques du système."""
    console.print("\n[bold yellow]Statistiques et statut[/bold yellow]")
    console.rule(style="yellow")

    # Charger les données
    try:
        # Chargement des fichiers JSON
        with open(script_dir / "bd_videos.json", "r", encoding="utf-8") as f:
            bd_videos = json.load(f)

        with open(script_dir / "emissions_def.json", "r", encoding="utf-8") as f:
            emissions_def = json.load(f)

        with open(script_dir / "listegeneration.json", "r", encoding="utf-8") as f:
            liste_gen = json.load(f)

        with open(script_dir / "messages.json", "r", encoding="utf-8") as f:
            messages = json.load(f)

    except FileNotFoundError as e:
        console.print(f"[bold red]Erreur:[/bold red] Fichier manquant - {e.filename}")
        return
    except json.JSONDecodeError as e:
        console.print(f"[bold red]Erreur:[/bold red] Fichier JSON invalide - {str(e)}")
        return

    # 1. Statistiques des séries
    console.print("\n[bold cyan]📺 Séries disponibles[/bold cyan]")
    table_series = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table_series.add_column("Série", style="cyan")
    table_series.add_column("Nombre d'épisodes", justify="right", style="green")
    table_series.add_column("Prochain épisode", justify="right", style="yellow")

    for serie in emissions_def.get("series", []):
        nom = serie.get("nom", "N/A")
        nb_episodes = serie.get("nb_episodes", 0)
        prochain = serie.get("prochain", "N/A")
        ordre = serie.get("ordre", "aléatoire")

        if ordre == "sequentiel":
            prochain_str = f"#{prochain}"
        else:
            prochain_str = "aléatoire"

        table_series.add_row(nom, str(nb_episodes), prochain_str)

    console.print(table_series)

    # 2. Statistiques des émissions
    console.print("\n[bold cyan]📋 Liste de génération[/bold cyan]")
    emissions = liste_gen.get("emissions", [])
    emissions_generees = sum(1 for e in emissions if e.get("genere", False))
    emissions_totales = len(emissions)

    table_emissions = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table_emissions.add_column("Statut", style="cyan")
    table_emissions.add_column("Nombre", justify="right", style="green")

    table_emissions.add_row("Émissions générées", f"[green]{emissions_generees}[/green]")
    table_emissions.add_row("Émissions à générer", f"[yellow]{emissions_totales - emissions_generees}[/yellow]")
    table_emissions.add_row("Total", f"[bold]{emissions_totales}[/bold]")

    console.print(table_emissions)

    # Afficher les prochaines émissions à générer
    if emissions_totales > emissions_generees:
        console.print("\n[bold cyan]🎬 Prochaines émissions à générer[/bold cyan]")
        table_prochaines = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        table_prochaines.add_column("Date", style="cyan")
        table_prochaines.add_column("Titre", style="yellow")
        table_prochaines.add_column("Description", style="dim")

        count = 0
        for emission in emissions:
            if not emission.get("genere", False) and count < 5:
                table_prochaines.add_row(
                    emission.get("date_diffusion", "N/A"),
                    emission.get("titre", "N/A"),
                    emission.get("description", "N/A")[:50] + "..."
                )
                count += 1

        console.print(table_prochaines)

    # 3. Statistiques des messages
    console.print("\n[bold cyan]💬 Messages IA[/bold cyan]")
    table_messages = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table_messages.add_column("Sujet", style="cyan")
    table_messages.add_column("Total", justify="right", style="green")
    table_messages.add_column("Générés", justify="right", style="yellow")
    table_messages.add_column("Non générés", justify="right", style="red")

    for sujet, msgs in messages.get("Messages", {}).items():
        total = len(msgs)
        generes = sum(1 for m in msgs if m.get("genere", False))
        non_generes = total - generes

        table_messages.add_row(
            sujet,
            str(total),
            f"[green]{generes}[/green]",
            f"[red]{non_generes}[/red]"
        )

    console.print(table_messages)

    # 4. Dernière activité
    console.print("\n[bold cyan]🕒 Dernière activité[/bold cyan]")
    try:
        log_path = script_dir / "log.txt"
        if log_path.exists():
            with open(log_path, "r", encoding="utf-8") as f:
                lignes = f.readlines()
                if lignes:
                    derniere_ligne = lignes[-1].strip()
                    console.print(f"  [dim]{derniere_ligne}[/dim]")
                else:
                    console.print("  [dim]Aucune activité enregistrée[/dim]")
        else:
            console.print("  [dim]Fichier de log non trouvé[/dim]")
    except Exception as e:
        console.print(f"  [dim]Erreur lors de la lecture du log: {str(e)}[/dim]")

    console.print()


def editer_liste_generation():
    """Permet d'éditer la liste de génération de manière interactive."""
    console.print("\n[bold yellow]Éditer la liste de génération[/bold yellow]")
    console.rule(style="yellow")

    try:
        liste_path = script_dir / "listegeneration.json"
        with open(liste_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        emissions = data.get("emissions", [])

        if not emissions:
            console.print("[yellow]Aucune émission dans la liste de génération[/yellow]")
            return

        # Menu d'édition
        while True:
            choix = questionary.select(
                "Que voulez-vous faire?",
                choices=[
                    "Voir la liste des émissions",
                    "Marquer une émission comme générée",
                    "Marquer une émission comme non générée",
                    "Supprimer une émission",
                    "Retour au menu principal"
                ]
            ).ask()

            if not choix or choix == "Retour au menu principal":
                break

            if choix == "Voir la liste des émissions":
                table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
                table.add_column("#", style="cyan", justify="right")
                table.add_column("Date", style="cyan")
                table.add_column("Titre", style="yellow")
                table.add_column("Généré", justify="center")
                table.add_column("Description", style="dim")

                for i, emission in enumerate(emissions, 1):
                    genere = "✓" if emission.get("genere", False) else "✗"
                    style_genere = "green" if emission.get("genere", False) else "red"

                    table.add_row(
                        str(i),
                        emission.get("date_diffusion", "N/A"),
                        emission.get("titre", "N/A"),
                        f"[{style_genere}]{genere}[/{style_genere}]",
                        emission.get("description", "N/A")[:40] + "..."
                    )

                console.print("\n")
                console.print(table)
                console.print()

            elif choix == "Marquer une émission comme générée":
                choices = [
                    f"{i}. {e.get('date_diffusion')} - {e.get('titre')} {'[DÉJÀ GÉNÉRÉ]' if e.get('genere', False) else ''}"
                    for i, e in enumerate(emissions, 1)
                ]
                choices.append("Annuler")

                selection = questionary.select(
                    "Quelle émission?",
                    choices=choices
                ).ask()

                if selection and selection != "Annuler":
                    index = int(selection.split(".")[0]) - 1
                    emissions[index]["genere"] = True

                    with open(liste_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)

                    console.print(f"[green]✓ Émission marquée comme générée[/green]")

            elif choix == "Marquer une émission comme non générée":
                choices = [
                    f"{i}. {e.get('date_diffusion')} - {e.get('titre')} {'[DÉJÀ GÉNÉRÉ]' if e.get('genere', False) else ''}"
                    for i, e in enumerate(emissions, 1)
                ]
                choices.append("Annuler")

                selection = questionary.select(
                    "Quelle émission?",
                    choices=choices
                ).ask()

                if selection and selection != "Annuler":
                    index = int(selection.split(".")[0]) - 1
                    emissions[index]["genere"] = False

                    with open(liste_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)

                    console.print(f"[green]✓ Émission marquée comme non générée[/green]")

            elif choix == "Supprimer une émission":
                choices = [
                    f"{i}. {e.get('date_diffusion')} - {e.get('titre')}"
                    for i, e in enumerate(emissions, 1)
                ]
                choices.append("Annuler")

                selection = questionary.select(
                    "Quelle émission supprimer?",
                    choices=choices
                ).ask()

                if selection and selection != "Annuler":
                    index = int(selection.split(".")[0]) - 1
                    emission_supprimee = emissions.pop(index)

                    with open(liste_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)

                    console.print(f"[green]✓ Émission supprimée: {emission_supprimee.get('titre')}[/green]")

    except FileNotFoundError:
        console.print("[bold red]Erreur:[/bold red] Fichier listegeneration.json non trouvé")
    except json.JSONDecodeError:
        console.print("[bold red]Erreur:[/bold red] Fichier listegeneration.json invalide")
    except Exception as e:
        console.print(f"[bold red]Erreur:[/bold red] {str(e)}")


def menu_principal():
    """Affiche le menu principal et gère les choix de l'utilisateur."""
    while True:
        afficher_banniere()

        choix = questionary.select(
            "Que voulez-vous faire?",
            choices=[
                "1. Scanner les vidéos",
                "2. Générer la liste d'émissions",
                "3. Générer les messages IA",
                "4. Régénérer l'émission du jour",
                "5. Éditer la liste de génération",
                "6. Afficher le statut et statistiques",
                "7. Quitter"
            ],
            use_shortcuts=True
        ).ask()

        if not choix or choix.startswith("7"):
            console.print("\n[bold cyan]Au revoir! 👋[/bold cyan]\n")
            break

        if choix.startswith("1"):
            scanner_videos()
        elif choix.startswith("2"):
            generer_liste_emissions()
        elif choix.startswith("3"):
            generer_messages_ia()
        elif choix.startswith("4"):
            regenerer_emission_jour()
        elif choix.startswith("5"):
            editer_liste_generation()
        elif choix.startswith("6"):
            afficher_statistiques()

        # Pause avant de revenir au menu
        if not choix.startswith("7"):
            questionary.press_any_key_to_continue("Appuyez sur une touche pour continuer...").ask()
            console.clear()


def main():
    """Point d'entrée principal du CLI."""
    try:
        menu_principal()
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]Interruption par l'utilisateur[/bold yellow]")
        console.print("[bold cyan]Au revoir! 👋[/bold cyan]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Erreur inattendue:[/bold red] {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
