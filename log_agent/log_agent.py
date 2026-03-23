import docker
import os
import json
import time
import requests
from datetime import datetime, timedelta

# ==========================================
# CONFIGURATION ET VARIABLES
# ==========================================
OMNIROUTE_URL = os.getenv("OMNIROUTE_URL", "http://omniroute:20128/v1/chat/completions")
OMNIROUTE_API_KEY = os.getenv("OMNIROUTE_API_KEY")
MODEL = os.getenv("AI_MODEL", "kr/claude-sonnet-4.5")
REPORT_DIR = os.getenv("REPORT_DIR", "/reports")
INTERVAL_SECONDS = int(os.getenv("INTERVAL_SECONDS", 21600))  # 6h par défaut

CONTAINERS_TO_WATCH = [
    "mail_agent",
    "mail_agent_gmail",
    "omniroute",
    "zeroclaw",
]

# ==========================================
# FONCTIONS UTILITAIRES
# ==========================================
def log(message):
    """Affiche un message avec l'heure courante."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)

def get_container_logs(container_name, since_minutes=360):
    """Récupère les logs d'un conteneur Docker sur la période écoulée."""
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        since = datetime.utcnow() - timedelta(minutes=since_minutes)
        logs = container.logs(since=since, timestamps=True).decode("utf-8", errors="replace")
        status = container.status
        return {"status": status, "logs": logs, "error": None}
    except docker.errors.NotFound:
        return {"status": "not_found", "logs": "", "error": f"Conteneur '{container_name}' introuvable"}
    except Exception as e:
        return {"status": "error", "logs": "", "error": str(e)}

def analyze_with_claude(container_name, status, logs):
    """Envoie les logs à Claude pour analyse et résumé."""
    headers = {
        "Authorization": f"Bearer {OMNIROUTE_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""Tu es un assistant d'analyse de logs système. Analyse les logs suivants du conteneur Docker '{container_name}' et réponds UNIQUEMENT en JSON valide avec cette structure exacte :
{{
  "statut": "OK" | "WARNING" | "CRITICAL",
  "nb_erreurs": <nombre>,
  "nb_warnings": <nombre>,
  "nb_infos": <nombre>,
  "resume": "<résumé court en 1-2 phrases>",
  "actions_suggerees": ["<action1>", "<action2>"]
}}

Statut du conteneur : {status}
Logs (dernières 6h) :
{logs[:3000] if logs else "Aucun log disponible"}

Règles :
- CRITICAL si le conteneur est arrêté ou s'il y a des erreurs bloquantes répétées
- WARNING si des erreurs ponctuelles ou des comportements anormaux sont détectés
- OK si tout fonctionne normalement
- actions_suggerees peut être une liste vide [] si tout va bien
- Réponds UNIQUEMENT avec le JSON, sans texte autour"""

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }

    try:
        response = requests.post(OMNIROUTE_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content'].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        log(f"  ✗ Erreur analyse IA pour '{container_name}': {e}")
        return {
            "statut": "WARNING",
            "nb_erreurs": 0,
            "nb_warnings": 0,
            "nb_infos": 0,
            "resume": f"Impossible d'analyser les logs : {e}",
            "actions_suggerees": ["Vérifier la connexion à OmniRoute"]
        }

def determine_global_status(analyses):
    """Détermine le statut global à partir des analyses individuelles."""
    statuts = [a.get("statut", "OK") for a in analyses.values()]
    if "CRITICAL" in statuts:
        return "CRITICAL"
    if "WARNING" in statuts:
        return "WARNING"
    return "OK"

def save_report(report):
    """Sauvegarde le rapport JSON avec horodatage et met à jour le rapport courant."""
    os.makedirs(REPORT_DIR, exist_ok=True)

    # Rapport horodaté pour l'historique
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_path = os.path.join(REPORT_DIR, f"report_{timestamp_str}.json")
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log(f"  ✓ Rapport historique sauvegardé : {history_path}")

    # Rapport courant (écrasé à chaque cycle — pour Datto RMM)
    current_path = os.path.join(REPORT_DIR, "report_latest.json")
    with open(current_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log(f"  ✓ Rapport courant mis à jour : {current_path}")

# ==========================================
# BOUCLE PRINCIPALE
# ==========================================
def run_log_agent():
    log("=" * 50)
    log("Démarrage du cycle d'analyse des logs...")

    conteneurs_analyse = {}

    for container_name in CONTAINERS_TO_WATCH:
        log(f"[{container_name}] Récupération des logs...")
        result = get_container_logs(container_name)

        if result["error"]:
            log(f"  ✗ {result['error']}")
            conteneurs_analyse[container_name] = {
                "statut": "CRITICAL",
                "nb_erreurs": 1,
                "nb_warnings": 0,
                "nb_infos": 0,
                "resume": result["error"],
                "actions_suggerees": [f"Vérifier que le conteneur '{container_name}' est bien démarré"]
            }
            continue

        log(f"  → Analyse IA en cours...")
        analyse = analyze_with_claude(container_name, result["status"], result["logs"])
        conteneurs_analyse[container_name] = analyse
        log(f"  ✓ Statut : {analyse.get('statut')} — {analyse.get('resume', '')}")

    statut_global = determine_global_status(conteneurs_analyse)

    rapport = {
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "periode_analysee": "6h",
        "statut_global": statut_global,
        "conteneurs": conteneurs_analyse
    }

    save_report(rapport)
    log(f"Cycle terminé. Statut global : {statut_global}")
    log("=" * 50)

# ==========================================
# DÉMARRAGE AUTOMATIQUE
# ==========================================
if __name__ == "__main__":
    log("Agent de surveillance des logs démarré !")
    while True:
        run_log_agent()
        log(f"Mise en veille pour {INTERVAL_SECONDS // 3600}h...")
        time.sleep(INTERVAL_SECONDS)