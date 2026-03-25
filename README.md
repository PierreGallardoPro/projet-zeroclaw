# 🦾 projet-zeroclaw

Plateforme d'**agents IA autonomes** propulsée par **ZeroClaw**, **OmniRoute** et **Claude (Anthropic)** — orchestrée via Docker.

---

## Architecture

```
projet-zeroclaw/
├── docker-compose.yml
├── .env
│
├── mail_agent/               # Agent de tri — boîte OVH / IMAP générique
│   ├── mail_agent.py
│   ├── logger.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── mail_agent_gmail/         # Agent de tri — boîte Gmail
│   ├── mail_agent.py
│   ├── logger.py
│   ├── requirements.txt
│   └── Dockerfile
│
└── log_viewer/               # Interface web de visualisation des logs
    ├── log_viewer.py
    └── Dockerfile
```

### Services Docker

| Service | Rôle | Port |
|---|---|---|
| `omniroute` | Routeur LLM — proxy les requêtes vers les providers IA | `20128` |
| `zeroclaw` | Gateway IA — gère les modèles et les accès | `42617` |
| `mail-agent` | Tri automatique des e-mails OVH / IMAP | — |
| `mail-agent-gmail` | Tri automatique des e-mails Gmail | — |
| `log-viewer` | Interface web des logs (accès via tunnel SSH) | `8080` (localhost uniquement) |

---

## Fonctionnement des agents

Chaque agent se connecte à la boîte mail via IMAP, récupère les e-mails non lus, envoie le sujet + un extrait à Claude via OmniRoute, puis déplace l'e-mail dans le dossier suggéré. Cycle toutes les **15 minutes**.

```
Boîte mail (IMAP) ──▶ Agent ──▶ OmniRoute ──▶ Claude
                         └──▶ Déplace l'e-mail dans le bon dossier
```

Les logs de tous les agents sont écrits dans un volume partagé (`agents-logs`) au format JSONL et consultables via le log viewer.

---

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/PierreGallardoPro/projet-zeroclaw.git
cd projet-zeroclaw
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Éditer `.env` :

```env
# Boîte OVH / IMAP
MAIL_USER=ton.email@tondomaine.com
MAIL_PASS=ton_mot_de_passe
IMAP_HOST=ssl0.ovh.net
IMAP_PORT=993

# Boîte Gmail
GMAIL_USER=ton.email@gmail.com
GMAIL_APP_PASS=ton_mot_de_passe_app_google

# IA
OMNIROUTE_API_KEY=ta_cle_api_omniroute
AI_MODEL=kr/claude-sonnet-4.5
```

> Pour Gmail : activer l'accès IMAP dans les paramètres Gmail et générer un mot de passe d'application sur [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

### 3. Lancer tous les services

```bash
docker compose up -d --build
```

---

## Visualiser les logs

Le log viewer est accessible uniquement via un **tunnel SSH** — le port 8080 n'est jamais exposé sur internet.

**Depuis Windows (PowerShell) :**

```
ssh -N -L 8080:127.0.0.1:8080 user@IP_SERVEUR
```

Puis ouvrir **http://localhost:8080** dans le navigateur.

**Raccourci `.bat` (double-clic) :**

```bat
@echo off
start /b ssh -N -L 8080:127.0.0.1:8080 user@IP_SERVEUR
timeout /t 2 >nul
start http://localhost:8080
```

---

## Commandes utiles

```bash
# Statut des conteneurs
docker compose ps

# Logs en temps réel d'un agent
docker compose logs -f mail-agent
docker compose logs -f mail-agent-gmail

# Relancer un agent spécifique
docker compose restart mail-agent

# Rebuild après modification du code
docker compose up -d --build mail-agent

# Arrêter tout
docker compose down
```

---

## Ajouter un nouvel agent

1. Créer un dossier `mon_agent/` avec `agent.py`, `logger.py`, `requirements.txt`, `Dockerfile`
2. Ajouter le service dans `docker-compose.yml` :

```yaml
mon-agent:
  build: ./mon_agent
  container_name: mon_agent
  restart: unless-stopped
  env_file:
    - .env
  environment:
    - OMNIROUTE_URL=http://omniroute:20128/v1/chat/completions
    - LOG_FILE=/app/logs/agents.jsonl
    - AGENT_NAME=mon-agent
  volumes:
    - agents-logs:/app/logs
  networks:
    - zeroclaw-net
  depends_on:
    omniroute:
      condition: service_healthy
```

3. Déployer :

```bash
docker compose up -d --build mon-agent
```

---

## Sécurité

- Le fichier `.env` doit être en `chmod 600` et appartenir à `root`
- Ne jamais déclarer les variables sensibles sous la clé `environment:` dans `docker-compose.yml` — utiliser uniquement `env_file`
- Le port `8080` du log viewer est bindé sur `127.0.0.1` uniquement — inaccessible sans tunnel SSH

---

## Licence

MIT