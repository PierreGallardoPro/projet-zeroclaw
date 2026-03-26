# 🦾 projet-zeroclaw

Plateforme d'**agents IA autonomes** propulsée par **ZeroClaw**, **OmniRoute** et **Claude (Anthropic)** — orchestrée via Docker.

---

## Architecture

```
projet-zeroclaw/
├── docker-compose.yml
├── .env
├── workspace/                # Dossier partagé avec le code-agent
│   ├── INSTRUCTIONS.md       # ← Tu écris tes instructions ici
│   └── RESPONSE.md           # ← Claude écrit sa réponse ici
│
├── mail_agent/               # Agent de tri — boîte OVH / IMAP
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
├── code_agent/               # Agent de codage autonome
│   ├── code_agent.py
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
| `code-agent` | Génère et écrit du code depuis des instructions | — |
| `log-viewer` | Interface web des logs (accès via tunnel SSH) | `8080` |

---

## Agents

### 📬 mail-agent / mail-agent-gmail

Connexion IMAP → récupération des e-mails non lus → classification par Claude → déplacement dans le bon dossier. Cycle toutes les 15 minutes.

### 🤖 code-agent

Surveille le fichier `workspace/INSTRUCTIONS.md`. Dès qu'il est modifié, il envoie l'instruction à Claude qui génère du code et l'écrit directement dans le workspace.

**Flux :**
```
Tu modifies workspace/INSTRUCTIONS.md
        ↓
code-agent détecte la modification
        ↓
Claude génère le code via OmniRoute
        ↓
Les fichiers sont écrits dans workspace/
        ↓
workspace/RESPONSE.md contient le résumé complet
```

**Comment utiliser le code-agent :**

1. Ouvre `workspace/INSTRUCTIONS.md` sur le serveur
2. Remplace le contenu par ton instruction, par exemple :

```
Crée une API Flask avec deux routes :
- GET /hello → retourne {"message": "Hello World"}
- GET /status → retourne {"status": "ok", "uptime": secondes depuis démarrage}
```

3. Sauvegarde le fichier — l'agent réagit dans la seconde
4. Consulte `workspace/RESPONSE.md` pour voir ce que Claude a fait
5. Les fichiers générés apparaissent directement dans `workspace/`

**Format que Claude utilise pour créer les fichiers :**

Claude structure ses réponses avec des blocs ` ```langage:chemin/fichier ``` ` :

````
```python:app.py
from flask import Flask
app = Flask(__name__)
...
```

```requirements.txt:requirements.txt
flask==3.0.0
```
````

---

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/PierreGallardoPro/projet-zeroclaw.git
cd projet-zeroclaw
```

### 2. Créer le dossier workspace

```bash
mkdir -p workspace
```

### 3. Configurer les variables d'environnement

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

### 4. Lancer tous les services

```bash
docker compose up -d --build
```

---

## Visualiser les logs

Le log viewer est accessible via un **tunnel SSH** — le port 8080 n'est jamais exposé sur internet.

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

Les logs de chaque agent sont identifiés par couleur. Les champs contextuels (fichiers écrits, taille, langage, erreur) apparaissent sous chaque ligne sous forme de badges.

---

## Commandes utiles

```bash
# Statut des conteneurs
docker compose ps

# Logs en temps réel
docker compose logs -f code-agent
docker compose logs -f mail-agent

# Rebuild d'un agent spécifique
docker compose up -d --build code-agent

# Arrêter tout
docker compose down
```

---

## Ajouter un nouvel agent

1. Créer `mon_agent/` avec `agent.py`, `logger.py`, `requirements.txt`, `Dockerfile`
2. Ajouter dans `docker-compose.yml` :

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

- Le fichier `.env` doit être en `chmod 600`
- Ne jamais mettre de variables sensibles sous `environment:` dans `docker-compose.yml` — utiliser uniquement `env_file`
- Le port `8080` est bindé sur `127.0.0.1` uniquement — inaccessible sans tunnel SSH

---

## Licence

MIT