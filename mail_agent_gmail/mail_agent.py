import imaplib
import email
from email.header import decode_header
import requests
import os
import time
import unicodedata
from datetime import datetime
from logger import log_info, log_error

# ==========================================
# CONFIGURATION ET VARIABLES
# ==========================================
GMAIL_USER       = os.getenv("GMAIL_USER")
GMAIL_APP_PASS   = os.getenv("GMAIL_APP_PASS")
OMNIROUTE_URL    = os.getenv("OMNIROUTE_URL")
OMNIROUTE_API_KEY= os.getenv("OMNIROUTE_API_KEY")
MODEL            = os.getenv("AI_MODEL")

MAX_RETRIES      = 3
RETRY_DELAY      = 10
HTTP_TIMEOUT     = 15

# ==========================================
# VALIDATION AU DÉMARRAGE
# ==========================================
def validate_env():
    required = {
        "GMAIL_USER": GMAIL_USER,
        "GMAIL_APP_PASS": GMAIL_APP_PASS,
        "OMNIROUTE_API_KEY": OMNIROUTE_API_KEY,
    }
    missing = [key for key, val in required.items() if not val]
    if missing:
        raise EnvironmentError(
            f"Variables d'environnement manquantes : {', '.join(missing)}\n"
            f"Vérifier le fichier .env avant de relancer le conteneur."
        )
    log_info("Variables d'environnement validées.")

# ==========================================
# FONCTIONS UTILITAIRES
# ==========================================
def decode_mime_words(s):
    return u''.join(
        word.decode(charset or 'utf-8') if isinstance(word, bytes) else word
        for word, charset in decode_header(s)
    )

def clean_folder_name(name):
    name_no_accents = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
    return name_no_accents.replace('"', '').replace("'", "").replace(" ", "_").strip()

def ask_claude_for_category(subject, snippet):
    headers = {
        "Authorization": f"Bearer {OMNIROUTE_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = (
        "Tu es un assistant de tri d'e-mails. Analyse cet e-mail et réponds UNIQUEMENT par le nom "
        "du dossier (libellé) dans lequel il doit être rangé. Choisis un nom court (1 à 2 mots maximum, "
        "ex: 'Factures', 'Newsletters', 'Personnel', 'Projets'). N'utilise AUCUN accent (remplace é par e, etc.). "
        "Aucune ponctuation, aucune phrase, juste le nom du dossier.\n\n"
        f"Objet : {subject}\nExtrait : {snippet}"
    )
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    try:
        response = requests.post(OMNIROUTE_URL, headers=headers, json=payload, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        category = response.json()['choices'][0]['message']['content'].strip()
        return clean_folder_name(category)
    except requests.exceptions.Timeout:
        log_error(f"Timeout OmniRoute ({HTTP_TIMEOUT}s) — classé dans A_Trier")
        return "A_Trier"
    except requests.exceptions.ConnectionError:
        log_error("OmniRoute inaccessible — classé dans A_Trier")
        return "A_Trier"
    except Exception as e:
        log_error(f"Erreur avec l'IA : {e}")
        return "A_Trier"

# ==========================================
# BOUCLE PRINCIPALE
# ==========================================
def run_mail_agent():
    log_info("Connexion à Gmail...")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(GMAIL_USER, GMAIL_APP_PASS)
            log_info("Connecté avec succès.")
            break
        except Exception as e:
            log_error(f"Tentative {attempt}/{MAX_RETRIES} échouée : {e}")
            if attempt < MAX_RETRIES:
                log_info(f"Nouvel essai dans {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            else:
                log_error("Connexion IMAP impossible après 3 tentatives — cycle abandonné.")
                return

    try:
        mail.select("inbox")
        status, messages = mail.search(None, "UNSEEN")
        email_ids = messages[0].split()

        if not email_ids:
            log_info("Aucun nouvel e-mail à trier.")
            mail.logout()
            return

        log_info(f"{len(email_ids)} e-mail(s) non lu(s) trouvé(s).")

        for i, e_id in enumerate(email_ids, start=1):
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = decode_mime_words(msg.get("Subject", "Sans Objet"))

                    log_info(f"[{i}/{len(email_ids)}] Traitement : \"{subject}\"")

                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                try:
                                    body = part.get_payload(decode=True).decode()
                                    break
                                except: pass
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode()
                        except: pass

                    snippet = body[:500].replace('\n', ' ')

                    log_info("Envoi à l'IA...")
                    folder_name = ask_claude_for_category(subject, snippet)
                    log_info(f"Classé dans : '{folder_name}'")

                    mail.create(f'"{folder_name}"')
                    result = mail.copy(e_id, f'"{folder_name}"')
                    if result[0] == 'OK':
                        mail.store(e_id, '+FLAGS', '\\Deleted')
                        log_info("E-mail déplacé avec succès.")
                    else:
                        log_error("Échec du déplacement.")

                    time.sleep(1)

        mail.expunge()
        mail.logout()
        log_info("Tri terminé avec succès.")

    except Exception as e:
        log_error(f"Erreur critique lors du traitement : {e}")

# ==========================================
# DÉMARRAGE AUTOMATIQUE
# ==========================================
if __name__ == "__main__":
    validate_env()
    log_info("Agent de tri démarré !")
    while True:
        run_mail_agent()
        log_info("Mise en veille pour 15 minutes...")
        time.sleep(900)