import imaplib
import email
from email.header import decode_header
import requests
import os
import time

# Récupération des variables d'environnement sécurisées
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS")
OMNIROUTE_URL = os.getenv("OMNIROUTE_URL")
OMNIROUTE_API_KEY = os.getenv("OMNIROUTE_API_KEY")
MODEL = os.getenv("AI_MODEL")

def decode_mime_words(s):
    return u''.join(
        word.decode(charset or 'utf-8') if isinstance(word, bytes) else word
        for word, charset in decode_header(s)
    )

def ask_claude_for_category(subject, snippet):
    headers = {
        "Authorization": f"Bearer {OMNIROUTE_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"Tu es un assistant de tri d'e-mails. Analyse cet e-mail et réponds UNIQUEMENT par le nom du dossier (libellé) dans lequel il doit être rangé. Choisis un nom court (1 à 2 mots maximum, ex: 'Factures', 'Newsletters', 'Personnel', 'Projets'). Aucune ponctuation, aucune phrase, juste le nom du dossier.\n\nObjet : {subject}\nExtrait : {snippet}"
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    try:
        response = requests.post(OMNIROUTE_URL, headers=headers, json=payload)
        response.raise_for_status()
        category = response.json()['choices'][0]['message']['content'].strip()
        return category.replace('"', '').replace("'", "")
    except Exception as e:
        print(f"Erreur avec l'IA: {e}")
        return "A_Trier"

def run_mail_agent():
    print("Connexion à Gmail...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASS)
        mail.select("inbox")
        
        status, messages = mail.search(None, "UNSEEN")
        email_ids = messages[0].split()

        if not email_ids:
            print("Aucun nouvel e-mail à trier.")
            mail.logout()
            return

        print(f"{len(email_ids)} e-mail(s) non lu(s) trouvé(s).")

        for e_id in email_ids:
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = decode_mime_words(msg.get("Subject", "Sans Objet"))
                    
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
                    
                    folder_name = ask_claude_for_category(subject, snippet)
                    print(f"[{subject}] -> Dossier '{folder_name}'")

                    mail.create(f'"{folder_name}"')
                    result = mail.copy(e_id, f'"{folder_name}"')
                    if result[0] == 'OK':
                        mail.store(e_id, '+FLAGS', '\\Deleted')
                    time.sleep(1)

        mail.expunge()
        mail.logout()
        print("Tri terminé avec succès.")
        
    except Exception as e:
        print(f"Erreur critique lors du traitement : {e}")

if __name__ == "__main__":
    while True:
        run_mail_agent()
        print("Mise en veille pour 15 minutes...")
        time.sleep(900) # Attente de 900 secondes (15 min) avant le prochain cycle