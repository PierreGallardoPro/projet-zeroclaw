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

def generate_html(report):
    """Génère un rapport HTML lisible depuis le rapport JSON."""
    statut_global = report["statut_global"]
    timestamp = report["timestamp"]
    conteneurs = report["conteneurs"]

    color_map = {"OK": "#3B6D11", "WARNING": "#854F0B", "CRITICAL": "#A32D2D"}
    bg_map    = {"OK": "#EAF3DE", "WARNING": "#FAEEDA", "CRITICAL": "#FCEBEB"}
    label_map = {"OK": "✓ OK", "WARNING": "⚠ WARNING", "CRITICAL": "✗ CRITICAL"}

    global_color = color_map.get(statut_global, "#444")
    global_bg    = bg_map.get(statut_global, "#eee")

    rows = ""
    for name, data in conteneurs.items():
        statut  = data.get("statut", "OK")
        resume  = data.get("resume", "")
        actions = data.get("actions_suggerees", [])
        erreurs = data.get("nb_erreurs", 0)
        warnings= data.get("nb_warnings", 0)
        infos   = data.get("nb_infos", 0)

        badge_color = color_map.get(statut, "#444")
        badge_bg    = bg_map.get(statut, "#eee")
        badge_label = label_map.get(statut, statut)

        actions_html = ""
        if actions:
            items = "".join(f"<li>{a}</li>" for a in actions)
            actions_html = f"<ul style='margin:6px 0 0 16px;padding:0;font-size:12px;color:#854F0B'>{items}</ul>"

        rows += f"""
        <tr>
          <td style='padding:12px 16px;font-weight:500;font-size:14px'>{name}</td>
          <td style='padding:12px 16px;text-align:center'>
            <span style='background:{badge_bg};color:{badge_color};padding:3px 10px;border-radius:6px;font-size:12px;font-weight:500'>{badge_label}</span>
          </td>
          <td style='padding:12px 16px;font-size:13px;color:#E24B4A;text-align:center'>{erreurs}</td>
          <td style='padding:12px 16px;font-size:13px;color:#BA7517;text-align:center'>{warnings}</td>
          <td style='padding:12px 16px;font-size:13px;color:#185FA5;text-align:center'>{infos}</td>
          <td style='padding:12px 16px;font-size:13px'>{resume}{actions_html}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ZeroClaw — Rapport logs</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f3; margin: 0; padding: 24px; color: #2c2c2a; }}
    .container {{ max-width: 900px; margin: 0 auto; }}
    .header {{ background: white; border-radius: 12px; padding: 24px 28px; margin-bottom: 16px; border: 0.5px solid #d3d1c7; display: flex; justify-content: space-between; align-items: center; }}
    .title {{ font-size: 20px; font-weight: 500; margin: 0 0 4px; }}
    .subtitle {{ font-size: 13px; color: #888780; margin: 0; }}
    .global-badge {{ padding: 8px 20px; border-radius: 8px; font-weight: 500; font-size: 15px; background: {global_bg}; color: {global_color}; }}
    .card {{ background: white; border-radius: 12px; border: 0.5px solid #d3d1c7; overflow: hidden; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{ background: #f5f5f3; padding: 10px 16px; text-align: left; font-size: 12px; font-weight: 500; color: #888780; text-transform: uppercase; letter-spacing: .04em; border-bottom: 0.5px solid #d3d1c7; }}
    tr:not(:last-child) td {{ border-bottom: 0.5px solid #f1efe8; }}
    tr:hover td {{ background: #fafaf8; }}
    .footer {{ text-align: center; font-size: 12px; color: #b4b2a9; margin-top: 16px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <p class="title">🦾 ZeroClaw — Rapport de surveillance</p>
        <p class="subtitle">Période analysée : 6h &nbsp;·&nbsp; Généré le {timestamp}</p>
      </div>
      <span class="global-badge">{label_map.get(statut_global, statut_global)}</span>
    </div>
    <div class="card">
      <table>
        <thead>
          <tr>
            <th>Conteneur</th>
            <th style='text-align:center'>Statut</th>
            <th style='text-align:center'>Erreurs</th>
            <th style='text-align:center'>Warnings</th>
            <th style='text-align:center'>Infos</th>
            <th>Résumé / Actions</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <p class="footer">projet-zeroclaw &nbsp;·&nbsp; rapport généré automatiquement par log_agent</p>
  </div>
</body>
</html>"""
    return html

def save_report(report):
    """Sauvegarde le rapport JSON + HTML avec horodatage et met à jour les rapports courants."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── JSON horodaté (historique)
    history_json = os.path.join(REPORT_DIR, f"report_{timestamp_str}.json")
    with open(history_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log(f"  ✓ JSON historique : {history_json}")

    # ── JSON courant (pour Datto RMM)
    current_json = os.path.join(REPORT_DIR, "report_latest.json")
    with open(current_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    log(f"  ✓ JSON courant mis à jour : {current_json}")

    # ── HTML horodaté (historique)
    history_html = os.path.join(REPORT_DIR, f"report_{timestamp_str}.html")
    with open(history_html, "w", encoding="utf-8") as f:
        f.write(generate_html(report))
    log(f"  ✓ HTML historique : {history_html}")

    # ── HTML courant (lisible dans un navigateur)
    current_html = os.path.join(REPORT_DIR, "report_latest.html")
    with open(current_html, "w", encoding="utf-8") as f:
        f.write(generate_html(report))
    log(f"  ✓ HTML courant mis à jour : {current_html}")

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