from pathlib import Path
import sys

def verifier_fichier_existe(filename: str):
    """Valide la présence d'un fichier de configuration.

    Cette fonction s'assure que le fichier indiqué existe. Si ce n'est
    pas le cas, elle suggère de copier le fichier exemple portant
    l'extension ``.sample`` puis termine l'exécution du programme. Cela
    évite les erreurs liées à l'absence de données indispensables.
    """
    path = Path(filename)
    if not path.exists():
        sample = path.with_suffix(path.suffix + '.sample')
        print(
            f"Le fichier '{filename}' est manquant. Copiez '{sample.name}' ",
            "puis personnalisez-le avant de relancer l'application."
        )
        sys.exit(1)
