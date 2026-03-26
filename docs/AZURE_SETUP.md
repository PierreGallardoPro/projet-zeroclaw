# Configuration Azure AD — mail-agent-exchange

## 1. Créer l'application dans Azure AD

1. Aller sur https://portal.azure.com
2. Chercher "App registrations" → "New registration"
3. Nom : `zeroclaw-mail-agent` (ou ce que tu veux)
4. Account type : "Accounts in this organizational directory only"
5. Cliquer "Register"

→ Copier le **Application (client) ID** et le **Directory (tenant) ID** — ils vont dans `.env`.


## 2. Créer un secret client

1. Dans l'app → "Certificates & secrets" → "New client secret"
2. Description : `zeroclaw`, Expiration : 24 months
3. Cliquer "Add"

→ Copier la **Value** immédiatement (elle disparaît après fermeture de la page).


## 3. Ajouter les permissions API

1. Dans l'app → "API permissions" → "Add a permission"
2. Choisir "Microsoft Graph" → "Application permissions"
3. Chercher et cocher : `Mail.ReadWrite`
4. Cliquer "Add permissions"
5. Cliquer **"Grant admin consent for [ton organisation]"** (bouton bleu)
   → Sans cette étape, l'agent recevra des erreurs 403.


## 4. Ajouter les variables dans .env

```env
# Exchange Online — Microsoft Graph API
EXCHANGE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
EXCHANGE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
EXCHANGE_CLIENT_SECRET=ton_secret_client
EXCHANGE_MAILBOX=pierre@tonentreprise.com
```


## 5. Déployer

```bash
# Créer le dossier de l'agent
mkdir -p ~/projet-zeroclaw/mail_agent_exchange

# Copier les fichiers :
# mail_agent_exchange.py → mail_agent_exchange/mail_agent_exchange.py
# logger.py              → mail_agent_exchange/logger.py
# requirements.txt       → mail_agent_exchange/requirements.txt
# Dockerfile             → mail_agent_exchange/Dockerfile

# Ajouter le service dans docker-compose.yml (voir snippet)

# Lancer
docker compose up -d --build mail-agent-exchange

# Vérifier
docker logs -f mail_agent_exchange
```


## Dépannage

| Erreur | Cause | Solution |
|---|---|---|
| `AADSTS700016` | CLIENT_ID incorrect | Vérifier l'App ID dans Azure |
| `AADSTS7000215` | CLIENT_SECRET incorrect ou expiré | Régénérer un secret |
| `403 Forbidden` | Consentement admin non accordé | "Grant admin consent" dans API permissions |
| `404 Not Found` | EXCHANGE_MAILBOX incorrect | Vérifier l'adresse e-mail exacte |
| `AADSTS50034` | L'utilisateur n'existe pas dans le tenant | Vérifier que le compte est bien dans Microsoft 365 |
