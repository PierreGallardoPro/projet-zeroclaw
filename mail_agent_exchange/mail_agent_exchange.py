"""
mail_agent_exchange.py — Agent de tri pour Microsoft 365 / Exchange Online.

Authentification : OAuth2 Client Credentials (app-only, sans interaction utilisateur).
API : Microsoft Graph v1.0
Cycle : toutes les 15 minutes.

Prérequis Azure AD (voir README) :
  - Une app enregistrée avec le permission Mail.ReadWrite (application, pas delegated)
  - Un secret client généré
  - L'admin doit avoir accordé le consentement admin (Grant admin consent)
"""

import os
import time
import requests
from datetime import datetime, timezone
from logger import log_info, log_warn, log_error

# ==========================================
# CONFIGURATION
# ==========================================
TENANT_ID        = os.getenv("EXCHANGE_TENANT_ID")
CLIENT_ID        = os.getenv("EXCHANGE_CLIENT_ID")
CLIENT_SECRET    = os.getenv("EXCHANGE_CLIENT_SECRET")
MAILBOX          = os.getenv("EXCHANGE_MAILBOX")          # ex: pierre@tonentreprise.com
OMNIROUTE_URL    = os.getenv("OMNIROUTE_URL", "http://omniroute:20128/v1/chat/completions")
OMNIROUTE_API_KEY= os.getenv("OMNIROUTE_API_KEY", "")
MODEL            = os.getenv("AI_MODEL", "kr/claude-sonnet-4.5")

GRAPH_BASE       = "https://graph.microsoft.com/v1.0"
TOKEN_URL        = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
SCOPE            = "https://graph.microsoft.com/.default"
HTTP_TIMEOUT     = 30
CYCLE_SECONDS    = 900   # 15 minutes

# ==========================================
# VALIDATION
# ==========================================
def validate_env():
    required = {
        "EXCHANGE_TENANT_ID":     TENANT_ID,
        "EXCHANGE_CLIENT_ID":     CLIENT_ID,
        "EXCHANGE_CLIENT_SECRET": CLIENT_SECRET,
        "EXCHANGE_MAILBOX":       MAILBOX,
        "OMNIROUTE_API_KEY":      OMNIROUTE_API_KEY,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise EnvironmentError(
            f"Variables manquantes : {', '.join(missing)}\n"
            "Vérifier le fichier .env avant de relancer."
        )
    log_info("Variables d'environnement validées.", mailbox=MAILBOX)


# ==========================================
# TOKEN OAUTH2 (cache simple)
# ==========================================
_token_cache: dict = {}

def get_access_token() -> str | None:
    """Retourne un token valide, le renouvelle si expiré."""
    now = time.time()
    if _token_cache.get("token") and now < _token_cache.get("expires_at", 0) - 60:
        return _token_cache["token"]

    try:
        r = requests.post(TOKEN_URL, data={
            "grant_type":    "client_credentials",
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope":         SCOPE,
        }, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        _token_cache["token"]      = data["access_token"]
        _token_cache["expires_at"] = now + data.get("expires_in", 3600)
        log_info("Token OAuth2 obtenu.")
        return _token_cache["token"]
    except Exception as e:
        log_error(f"Erreur obtention token OAuth2 : {e}")
        return None


def graph_headers() -> dict:
    token = get_access_token()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ==========================================
# GRAPH API — UTILITAIRES
# ==========================================
def get_unread_messages() -> list[dict]:
    """Récupère les e-mails non lus de la boîte de réception."""
    url = (
        f"{GRAPH_BASE}/users/{MAILBOX}/mailFolders/inbox/messages"
        "?$filter=isRead eq false"
        "&$select=id,subject,bodyPreview,from"
        "&$top=50"
        "&$orderby=receivedDateTime desc"
    )
    try:
        r = requests.get(url, headers=graph_headers(), timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        return r.json().get("value", [])
    except Exception as e:
        log_error(f"Erreur récupération e-mails : {e}")
        return []


def get_or_create_folder(folder_name: str) -> str | None:
    """Retourne l'ID du dossier (le crée s'il n'existe pas)."""
    url = f"{GRAPH_BASE}/users/{MAILBOX}/mailFolders"
    try:
        r = requests.get(url, headers=graph_headers(), timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        folders = r.json().get("value", [])
        for f in folders:
            if f["displayName"].lower() == folder_name.lower():
                return f["id"]

        # Créer le dossier
        r2 = requests.post(url, headers=graph_headers(),
                           json={"displayName": folder_name},
                           timeout=HTTP_TIMEOUT)
        r2.raise_for_status()
        folder_id = r2.json()["id"]
        log_info(f"Dossier créé : {folder_name}")
        return folder_id
    except Exception as e:
        log_error(f"Erreur dossier '{folder_name}' : {e}")
        return None


def move_message(message_id: str, folder_id: str) -> bool:
    """Déplace un e-mail vers le dossier cible."""
    url = f"{GRAPH_BASE}/users/{MAILBOX}/messages/{message_id}/move"
    try:
        r = requests.post(url, headers=graph_headers(),
                          json={"destinationId": folder_id},
                          timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        return True
    except Exception as e:
        log_error(f"Erreur déplacement e-mail : {e}")
        return False


# ==========================================
# CLASSIFICATION IA
# ==========================================
def classify_email(subject: str, preview: str) -> str:
    """Envoie l'e-mail à Claude via OmniRoute pour classification."""
    prompt = (
        "Tu es un assistant de tri d'e-mails. Analyse cet e-mail et réponds UNIQUEMENT "
        "par le nom du dossier dans lequel il doit être rangé. "
        "Choisis un nom court (1 à 2 mots max, ex: Factures, Newsletters, Projets, RH). "
        "Aucun accent, aucune ponctuation, juste le nom du dossier.\n\n"
        f"Objet : {subject}\nExtrait : {preview[:500]}"
    )
    try:
        r = requests.post(
            OMNIROUTE_URL,
            headers={"Authorization": f"Bearer {OMNIROUTE_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
            timeout=30,
        )
        r.raise_for_status()
        folder = r.json()["choices"][0]["message"]["content"].strip()
        # Nettoyage basique
        folder = folder.replace('"', '').replace("'", '').replace(' ', '_')
        return folder or "A_Trier"
    except requests.exceptions.Timeout:
        log_error("Timeout OmniRoute — classé dans A_Trier")
        return "A_Trier"
    except Exception as e:
        log_error(f"Erreur IA : {e}")
        return "A_Trier"


# ==========================================
# BOUCLE PRINCIPALE
# ==========================================
def run_cycle():
    log_info("Début du cycle de tri...")

    messages = get_unread_messages()
    if not messages:
        log_info("Aucun e-mail non lu.")
        return

    log_info(f"{len(messages)} e-mail(s) non lu(s) trouvé(s).")

    for i, msg in enumerate(messages, 1):
        subject = msg.get("subject") or "(sans objet)"
        preview = msg.get("bodyPreview") or ""
        msg_id  = msg["id"]

        log_info(f"[{i}/{len(messages)}] Traitement : \"{subject[:60]}\"")

        folder_name = classify_email(subject, preview)
        log_info(f"Classé dans : '{folder_name}'")

        folder_id = get_or_create_folder(folder_name)
        if not folder_id:
            log_error(f"Impossible d'obtenir le dossier '{folder_name}' — e-mail ignoré.")
            continue

        if move_message(msg_id, folder_id):
            log_info(f"E-mail déplacé avec succès.", dossier=folder_name)
        else:
            log_error(f"Échec du déplacement.")

        time.sleep(1)

    log_info("Cycle terminé.")


# ==========================================
# POINT D'ENTRÉE
# ==========================================
if __name__ == "__main__":
    validate_env()
    log_info("Agent Exchange démarré.", mailbox=MAILBOX)
    while True:
        run_cycle()
        log_info(f"Mise en veille {CYCLE_SECONDS // 60} minutes...")
        time.sleep(CYCLE_SECONDS)