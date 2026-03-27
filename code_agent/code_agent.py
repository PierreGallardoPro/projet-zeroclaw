"""
code_agent.py — Agent de codage autonome.

Surveille INSTRUCTIONS.md dans le workspace. Dès qu'il est modifié,
envoie l'instruction à Claude via OmniRoute, parse les blocs de code
dans la réponse et écrit les fichiers dans le workspace.

Flux :
  INSTRUCTIONS.md modifié
      ↓
  Claude (via OmniRoute)
      ↓
  Parse les blocs ```langage:chemin/fichier.ext``` dans la réponse
      ↓
  Écrit les fichiers dans /app/workspace/
      ↓
  Écrit RESPONSE.md avec le résumé complet
"""

import os
import re
import time
import requests
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from logger import log_info, log_warn, log_error

# ==========================================
# CONFIGURATION
# ==========================================
OMNIROUTE_URL    = os.getenv("OMNIROUTE_URL")
OMNIROUTE_API_KEY= os.getenv("OMNIROUTE_API_KEY")
MODEL            = os.getenv("AI_MODEL")
WORKSPACE_DIR    = os.getenv("WORKSPACE_DIR", "/app/workspace")
INSTRUCTION_FILE = "INSTRUCTIONS.md"
RESPONSE_FILE    = "RESPONSE.md"
HTTP_TIMEOUT     = 180  # Les réponses de code peuvent être longues

SYSTEM_PROMPT = """Tu es un agent de codage expert intégré dans une plateforme d'automatisation.
Tu reçois des instructions en langage naturel et tu génères du code fonctionnel.

RÈGLES ABSOLUES :
1. Pour chaque fichier à créer ou modifier, utilise ce format EXACT :
   ```langage:chemin/relatif/fichier.ext
   contenu du fichier
   ```
   Exemples valides :
   ```python:app.py
   ```
   ```javascript:src/components/Button.jsx
   ```
   ```html:index.html
   ```

2. Tu peux créer autant de fichiers que nécessaire.
3. Donne toujours un résumé clair de ce que tu as fait après les blocs de code.
4. Si une instruction est ambiguë, fais des choix raisonnables et explique-les.
5. N'utilise JAMAIS de chemin absolu — toujours relatif au projet.
"""

# ==========================================
# APPEL À L'IA
# ==========================================
def call_claude(instruction: str) -> str | None:
    """Envoie l'instruction à Claude via OmniRoute et retourne le texte brut."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OMNIROUTE_API_KEY}",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": instruction},
        ],
        "temperature": 0.2,
        "max_tokens": 8192,
    }
    try:
        r = requests.post(OMNIROUTE_URL, json=payload, headers=headers, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        log_error(f"Timeout OmniRoute ({HTTP_TIMEOUT}s)")
        return None
    except requests.exceptions.ConnectionError:
        log_error("OmniRoute inaccessible")
        return None
    except Exception as e:
        log_error(f"Erreur appel IA : {e}")
        return None


# ==========================================
# PARSING DES BLOCS DE CODE
# ==========================================
def parse_code_blocks(response: str) -> list[dict]:
    """
    Extrait les blocs ```langage:chemin``` de la réponse de Claude.
    Retourne une liste de {"path": str, "lang": str, "content": str}.
    """
    pattern = r"```(\w+):([^\n`]+)\n(.*?)```"
    matches = re.findall(pattern, response, re.DOTALL)
    blocks = []
    for lang, path, content in matches:
        path = path.strip().lstrip("/")  # sécurité : jamais de chemin absolu
        blocks.append({"lang": lang, "path": path, "content": content.rstrip()})
    return blocks


# ==========================================
# ÉCRITURE DES FICHIERS
# ==========================================
def write_files(blocks: list[dict]) -> list[str]:
    """Écrit les fichiers dans le workspace. Retourne la liste des chemins écrits."""
    workspace = Path(WORKSPACE_DIR)
    written = []

    for block in blocks:
        target = (workspace / block["path"]).resolve()

        # Sécurité : refuser tout chemin qui sortirait du workspace
        try:
            target.relative_to(workspace.resolve())
        except ValueError:
            log_error(f"Chemin interdit refusé : {block['path']}")
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(block["content"], encoding="utf-8")
        written.append(block["path"])
        log_info(f"Fichier écrit : {block['path']}", lang=block["lang"], bytes=len(block["content"]))

    return written


# ==========================================
# HANDLER WATCHDOG
# ==========================================
class InstructionHandler(FileSystemEventHandler):
    """Réagit à la modification de INSTRUCTIONS.md."""

    # Anti-rebond : watchdog peut déclencher l'événement 2x de suite
    _last_trigger: float = 0.0
    _debounce_s: float = 2.0

    def on_modified(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith(INSTRUCTION_FILE):
            return

        now = time.time()
        if now - self._last_trigger < self._debounce_s:
            return
        self._last_trigger = now

        self._process(event.src_path)

    def _process(self, filepath: str):
        instruction_path = Path(filepath)
        instruction = instruction_path.read_text(encoding="utf-8").strip()

        # Ignorer les états initiaux vides ou la valeur par défaut
        if not instruction or instruction.startswith("# Écris tes instructions ici"):
            return

        log_info("Nouvelle instruction reçue", fichier=INSTRUCTION_FILE, longueur=len(instruction))

        # 1. Appel à Claude
        log_info("Envoi à Claude via OmniRoute...")
        response = call_claude(instruction)

        if not response:
            log_error("Pas de réponse de l'IA — cycle abandonné.")
            _write_response("❌ Erreur : pas de réponse de l'IA.")
            return

        log_info("Réponse reçue de l'IA", caracteres=len(response))

        # 2. Parser les blocs de code
        blocks = parse_code_blocks(response)

        if blocks:
            log_info(f"{len(blocks)} fichier(s) à écrire détecté(s)")
            written = write_files(blocks)
            log_info(f"Écriture terminée", fichiers=written)
        else:
            log_warn("Aucun bloc de code détecté dans la réponse — réponse textuelle uniquement.")

        # 3. Écrire RESPONSE.md avec la réponse complète
        _write_response(response)
        log_info(f"Réponse complète disponible dans {RESPONSE_FILE}")


# ==========================================
# UTILITAIRES
# ==========================================
def _write_response(content: str):
    """Écrit la réponse de l'IA dans RESPONSE.md dans le workspace."""
    path = Path(WORKSPACE_DIR) / RESPONSE_FILE
    path.write_text(content, encoding="utf-8")


def _init_workspace():
    """Crée le workspace et le fichier d'instructions s'ils n'existent pas."""
    workspace = Path(WORKSPACE_DIR)
    workspace.mkdir(parents=True, exist_ok=True)

    instruction_path = workspace / INSTRUCTION_FILE
    if not instruction_path.exists():
        instruction_path.write_text(
            "# Écris tes instructions ici...\n\n"
            "Exemple : Crée une application Flask avec une route GET /hello qui retourne 'Hello World'.\n",
            encoding="utf-8",
        )
        log_info(f"{INSTRUCTION_FILE} créé dans le workspace.")


# ==========================================
# POINT D'ENTRÉE
# ==========================================
def main():
    log_info("Agent de codage démarré", workspace=WORKSPACE_DIR, model=MODEL)
    _init_workspace()

    handler = InstructionHandler()
    observer = Observer()
    observer.schedule(handler, WORKSPACE_DIR, recursive=False)
    observer.start()
    log_info(f"Surveillance active sur {WORKSPACE_DIR}/{INSTRUCTION_FILE}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log_info("Arrêt demandé.")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()