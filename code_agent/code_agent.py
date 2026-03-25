import os
import time
import requests
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- CONFIGURATION ---
OMNIROUTE_URL = os.getenv("OMNIROUTE_URL", "http://omniroute:20128/v1/chat/completions")
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", "/app/workspace")
INSTRUCTION_FILE = "INSTRUCTIONS.md"
# On supposera que tu as ton propre fichier logger.py comme pour les autres agents
# from logger import log_action 

class CodeAgentHandler(FileSystemEventHandler):
    def on_modified(self, event):
        # On ne réagit que si c'est le fichier INSTRUCTIONS.md qui est modifié
        if not event.is_directory and event.src_path.endswith(INSTRUCTION_FILE):
            self.traiter_instruction(event.src_path)

    def traiter_instruction(self, filepath):
        print(f"👀 Nouvelle instruction détectée dans {INSTRUCTION_FILE}...")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                instruction = f.read().strip()
                
            if not instruction:
                return

            print("🚀 Envoi de la requête à OmniRoute...")
            
            # Préparation du payload pour OmniRoute (format standard OpenAI/Anthropic)
            payload = {
                "messages": [
                    {"role": "system", "content": "Tu es un agent de codage expert. Ton rôle est de générer ou modifier du code selon les instructions."},
                    {"role": "user", "content": instruction}
                ],
                "temperature": 0.2 # Basse température pour du code plus précis
            }

            headers = {"Content-Type": "application/json"}
            
            response = requests.post(OMNIROUTE_URL, json=payload, headers=headers)
            response.raise_for_status()
            
            reponse_ia = response.json()
            code_genere = reponse_ia['choices'][0]['message']['content']
            
            print("✅ Réponse reçue ! (Ici nous ajouterons la logique pour écrire les fichiers)")
            # log_action("code_agent", "success", "Code généré avec succès")
            
        except Exception as e:
            print(f"❌ Erreur lors du traitement : {e}")
            # log_action("code_agent", "error", str(e))

def main():
    print(f"🤖 Agent de codage démarré. Surveillance du dossier : {WORKSPACE_DIR}")
    
    # S'assurer que le dossier workspace existe
    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    
    # Création du fichier INSTRUCTIONS.md vide s'il n'existe pas
    instruction_path = os.path.join(WORKSPACE_DIR, INSTRUCTION_FILE)
    if not os.path.exists(instruction_path):
        with open(instruction_path, 'w') as f:
            f.write("# Écris tes instructions ici...\n")

    # Mise en place du Watchdog
    event_handler = CodeAgentHandler()
    observer = Observer()
    observer.schedule(event_handler, WORKSPACE_DIR, recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()