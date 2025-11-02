import json
import anthropic
from openai import OpenAI
import google.generativeai as genai
import time
import sys
try:
    import config
except ImportError:
    print("Le fichier 'config.py' est manquant. Copiez 'config.py.sample' puis personnalisez-le.")
    sys.exit(1)

from utils import verifier_fichier_existe

python_path = sys.executable  # Donne le chemin du python actif

# Configuration des clients API
client = anthropic.Client(api_key=config.ANTHROPIC_API_KEY)
clientOAI = OpenAI(api_key=config.OPENAI_API_KEY)
genai.configure(api_key=config.GEMINI_API_KEY)

config = {
    "anth_prompt": "claude-3-5-sonnet-20240620",
    "anth_message": "claude-3-5-sonnet-20240620", 
    "anth_description": "claude-3-5-sonnet-20240620",  
    "openai_prompt": "gpt-4o",
    "openai_message": "gpt-4o",
    "openai_description": "gpt-4o",  # Ajout de cette ligne
    "gemini_prompt": "gemini-1.5-pro-latest",
    "gemini_message": "gemini-1.5-pro-latest",
    "gemini_description": "gemini-1.5-pro-latest",  
    "system_content_prompt": """
Vous êtes un assistant inventif qui génère des instructions (prompts) à un modèle de langage pour qu'il génère des textes destinés à des enfants d'âge de 10 ans.
Vous aimez partager votre amour de l'imagination, votre intérêt sur le fonctionnement des choses, la compréhension du monde naturel, de l'histoire, de l'esprit critique et des livres.
Vous ne vous répétez pas. 
Vous trouvez de angles intéressants qui sont éducatifs, originaux et parfois étonnants ou fantaisistes.
Vos instructions sont spécifiques, claires: "Expliquez...", "Décrivez..." "Mentionnez obligatoirement...", "Présentez...", " etc. 
Jamais vous ne proposer de : montrer, dessiner, chanter, réaliser des activité interactives, bouger. Vous ne suggérez pas de poser de questions directes.
""",
    "system_content_message": """
Vous êtes la voix de Télé-Limoilou, une émission télévisée quotidienne pour Cécile et Françoise. Vous vous adressez à elles comme un adulte bienveillant le ferait. 
Vous introduisez en français les programmes avec un langage adapté aux enfants du Québec, sans utiliser d'anglicismes. 
Votre communication est chaleureuse, humoristique et éducative, visant à capter l'attention des enfants.
Les valeurs que vous transmettez sont:  amour de l'imagination, compréhension du monde naturel, l'importance de l'histoire, développement de l'esprit critique, passion pour lecture, comprendre et gérer ses émotions.
Vous commencez chaque message par une salutation engageante en vous présentant comme Télé Limoilou. 
Soyez engageant, faite de liens entre le sujet et la réalité des enfants. 
Évitez l'usage d'émoticônes, de retours à la ligne ou de caractères spéciaux. Les messages doivent éduquer et divertir tout en promouvant des valeurs positives. 
Vous ne pouvez par faire de jeux avec les enfants, vous n'êtes qu'une voix.
Vous pouvez faire référence à de précédents message quand cela est pertinent sans le faire systématiquement.
Concluez avec une salutation adressés aux deux fillettes et souhatez une bonne écoute de leurs émissions favorites. 
Assurez-vous que le contenu est toujours approprié et sécurisant pour les enfants, en évitant de promouvoir des stéréotypes ou des comportements négatifs. 
Expliquez les mots compliqués. 
""",
    "system_content_image": """
Vous générez des instruction claire et brèves pour la création d'une image. 
Votre réponse ne doit pas commencer par "Voici une description d'image" ou tout autre forme d'introduction.
Vous structurez votre réponse ainsi: 
Description: Vous décrivez avec précision le contenu de l'image: une scène simple et claire.
Style: Vous proposez un style spécifique: pour l'image, par exemple : comic book américain 4 colors process, anime japonais pour enfants des années 1970, illustration d'histoire d'aventure classique.  Ne vous limitez pas à ces exemples ou a des styles spécifiques aux enfants. Explorez les traditions et les cultures, montrez des style variés.
Ne proposez jamais d'éléments protégées par des droits d'auteur. IMPORTANT: Ne mentionnez jamais de des noms d'artistes ou d'entreprises.
Description du style: Vous décrivez brièvement le style, les techniques utilisées.
Atmosphère: L'atmosphère liée au style et au contenu
Palette: La palette de couleur générale, cohérente avec le style choisi
Interdisez strictement tout texte dans l'image et mentionnez systématiquement cette restriction.
""",
#    "num_prompts": 3,
    "text_length": "190",
    "generation_config": {
        "temperature": 1.2,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    },
    "safety_settings": [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH", 
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_ONLY_HIGH"
        },
    ],
}

def generate_prompts(subject, num_prompts, api_choice):
    """Crée une liste de suggestions de messages à partir d'un sujet."""
    prompt_message = (
        f"En vous assurant de ne pas répéter la même idée ou la même situation, "
        f"fournissez une liste de {num_prompts} prompts courts au format JSON explorant différents aspects concrets du sujet suivant "
        f"dans le but d'éduquer et de divertir : {subject}. "
        f"Pour le premier prompt, donnez en plus comme instruction de mentionner que c'est le premier message d'une série sur le sujet et pour le dernier demandez en plus de mentionner que c'est le dernier de la série. "
        f"Utilisez la structure json suivante pour répondre : {{\"prompts\": [\"liste des {num_prompts} prompts\"]}}."
    )

    if api_choice == "1":
        response = client.messages.create(
            model=config["anth_prompt"], 
            max_tokens=2000,
            temperature=1,
            system=config["system_content_prompt"],
            messages=[
                {"role": "user", "content": prompt_message},
                {"role": "assistant", "content": "{"}
            ]
        )
        prompts_json = response.content[0].text.strip()
        prompts = json.loads("{" + prompts_json)["prompts"]
    elif api_choice == "2":
        response = clientOAI.chat.completions.create(
            model=config["openai_prompt"],
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": config["system_content_prompt"]},
                {"role": "user", "content": prompt_message},
                {"role": "assistant", "content": "{"}
            ]
        )
        prompts_json = response.choices[0].message.content.strip()
        prompts = json.loads(prompts_json)["prompts"]
    else:
        model = genai.GenerativeModel(model_name=config["gemini_prompt"],
                                      generation_config=config["generation_config"],
                                      safety_settings=config["safety_settings"])
        
        convo = model.start_chat(history=[])
        response = convo.send_message(config["system_content_prompt"] + f"\n{prompt_message} Toujours débuter votre réponse avec {{")
        
        if response.candidates:
            prompts_json = response.candidates[0].content.parts[0].text.strip()
            prompts = json.loads(prompts_json)["prompts"]
        else:
            prompts = []

    return prompts



def generate_text(prompts, api_choice):
    """Génère le contenu textuel en suivant les prompts fournis."""
    texts = []
    history = []

    prompt_message = f"En vous basant sur le prompt suivant, proposez un texte de {config['text_length']} mots adapté aux enfants de 4 ans : {{prompt}}"

    if api_choice == "1":
        # Créer la session une fois au début pour Anthropic
        print("Début de la génération pour Anthropic")
        
        for prompt in prompts:
            user_message = prompt_message.format(prompt=prompt)
            print(f"Prompt : {prompt}")
            print(f"Historique actuel : {history}")
            messages = history + [{"role": "user", "content": user_message}]
            response = client.messages.create(
                model=config["anth_message"],
                max_tokens=2000,
                temperature=1,
                system=config["system_content_message"],
                messages=messages
            )
            text = response.content[0].text.strip()
            texts.append({"text": text})
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": text})
            print(f"Texte généré : {text}")
            print("Pause de trois secondes...")
            time.sleep(3)
    
    elif api_choice == "2":
        # Créer la session une fois au début pour OpenAI
        print("Début de la génération pour OpenAI")
        history.append({"role": "system", "content": config["system_content_message"]})
        for prompt in prompts:
            user_message = prompt_message.format(prompt=prompt)
            print(f"Prompt : {prompt}")
            print(f"Historique actuel : {history}")
            messages = history + [{"role": "user", "content": user_message}]
            response = clientOAI.chat.completions.create(
                model=config["openai_message"],
                messages=messages
            )
            text = response.choices[0].message.content.strip()
            texts.append({"text": text})
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": text})
            print(f"Texte généré : {text}")
            print("Pause de trois secondes...")
            time.sleep(3)
    
    else:
        # Créer la session une fois au début pour Gemini
        print("Début de la génération pour Gemini")
        model = genai.GenerativeModel(model_name=config["gemini_message"],
                                      system_instruction=config["system_content_message"],
                                      generation_config=config["generation_config"],
                                      safety_settings=config["safety_settings"])
        
        # Initialiser une session de chat
        chat = model.start_chat(history=[])
      #  system_message = {"role": "system", "parts": [{"text": config["system_content_message"]}]}
      #  chat.send_message({"text": config["system_content_message"]})
      #  history.append(system_message)

        for prompt in prompts:
            user_message = prompt_message.format(prompt=prompt)
            print(f"Prompt : {prompt}")
            print(f"Historique actuel : {history}")
            response = chat.send_message({"text": user_message})
            text = response.candidates[0].content.parts[0].text.strip()
            texts.append({"text": text})
            history.append({"role": "user", "content": user_message})
            history.append({"role": "model", "content": text})
            print(f"Texte généré : {text}")
            print("Pause de trois secondes...")
            time.sleep(3)
    
    return texts




def generate_image_description(text, api_choice):
    """Propose une courte description d'image pour illustrer un texte."""
    prompt_message = f"Proposez une description d'image pour illustrer le texte suivant de manière originale, sans tenir compte de la salutation au début du texte ou de celle à la fin : {text}"

    if api_choice == "1":
        response = client.messages.create(
            model=config["anth_description"],
            max_tokens=2000,
            temperature=1,
            system=config["system_content_image"],
            messages=[
                {"role": "user", "content": prompt_message}
            ]
        )
        description = response.content[0].text.strip()
    elif api_choice == "2":
        response = clientOAI.chat.completions.create(
            model=config["openai_description"],
            messages=[
                {"role": "system", "content": config["system_content_image"]},
                {"role": "user", "content": prompt_message}
            ]
        )
        description = response.choices[0].message.content.strip()
    else:
        model = genai.GenerativeModel(model_name=config["gemini_description"],
                                      generation_config=config["generation_config"],
                                      safety_settings=config["safety_settings"])
                                      
        convo = model.start_chat(history=[{"role": "user", "parts": [{"text": ""}]}])
                    # Send the system message first
        convo.send_message({"text": config["system_content_image"]})
        response = convo.send_message({"text": prompt_message})
        
        description = response.candidates[0].content.parts[0].text.strip()

    return description


def load_messages():
    """Charge le fichier ``messages.json`` s'il existe."""
    try:
        with open("messages.json", "r", encoding="utf-8") as file:
            data = json.load(file)
            return data["Messages"]
    except FileNotFoundError:
        return {}

def save_messages(data):
    """Sauvegarde la structure des messages dans ``messages.json``."""
    with open("messages.json", "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def main():
    """Flux interactif pour générer messages et images."""
    verifier_fichier_existe('messages.json')
    api_choice = input("Choisissez l'API à utiliser (1 pour Anthropic, 2 pour OpenAI, 3 pour Google Gemini) : ")
    subject = input("Entrez la description d'un sujet : ")
    print(f"Sujet : {subject}")

    # Demander le nombre de prompts à générer, avec une valeur par défaut de 7
    num_prompts = input("Entrez le nombre de prompts à générer (par défaut 7) : ")
    num_prompts = int(num_prompts) if num_prompts.isdigit() else 7  # Utiliser 7 comme valeur par défaut

    print(f"Nombre de prompts : {num_prompts}")

    messages = load_messages()

    print("Génération des prompts...")
    prompts = generate_prompts(subject, num_prompts, api_choice)
    print("Prompts générés :")
    print(json.dumps(prompts, indent=2, ensure_ascii=False))

    print("\nVoici les prompts générés. Vous pouvez les éditer ou les accepter tels quels.")
    for i, prompt in enumerate(prompts):
        print(f"\nPrompt {i+1} : {prompt}")
        choice = input("Voulez-vous éditer ce prompt ? (o/n) ")
        if choice.lower() == "o":
            print(f"Prompt original : {prompt}")
            prompts[i] = input("Entrez le nouveau prompt : ")

    print("\nGénération des textes...")
    generated_texts = generate_text(prompts, api_choice)

    print("\nGénération des descriptions d'images...")
    for content in generated_texts:
        image_description = generate_image_description(content["text"], api_choice)
        content["image_description"] = image_description
        print(f"Description d'image générée : {image_description}")
        time.sleep(3)

    if subject not in messages:
        messages[subject] = []

    existing_ids = [message["id"] for message in messages[subject]]
    next_id = max(existing_ids) + 1 if existing_ids else 1

    for i, content in enumerate(generated_texts):
        messages[subject].append({
            "id": next_id,
            "texteMessage": content["text"],
            "descriptionImage": content["image_description"],
            "genere": False
        })
        next_id += 1
        print(f"Texte et description d'image {i+1}/{len(generated_texts)} ajoutés à la liste des messages.")

    print("\nEnregistrement des messages dans messages.json...")
    save_messages({"Messages": messages})
    print("Le contenu de messages.json a été mis à jour avec succès.")

if __name__ == "__main__":
    main()


