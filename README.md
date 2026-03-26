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
| `log-viewer` | Interface web des logs | `8080` |

---

## Compatibilité

### 🐧 Linux / Serveur Debian (environnement principal)

Le projet est conçu pour tourner sur Linux. Aucune configuration supplémentaire.

```bash
# Prérequis
sudo apt install docker.io docker-compose-plugin

# Permissions workspace
mkdir -p workspace
chown 1000:1000 workspace
```

Accès au log viewer depuis ton PC via tunnel SSH :
```
ssh -N -L 8080:127.0.0.1:8080 user@IP_SERVEUR
```
Puis ouvrir `http://localhost:8080`.

---

### 🪟 Windows (Docker Desktop + WSL2)

Le projet fonctionne sur Windows via **Docker Desktop** et **WSL2**. Les conteneurs tournent dans un noyau Linux — le comportement est identique au serveur.

**Prérequis :**

1. Activer WSL2 (PowerShell en administrateur) :
```powershell
wsl --install
```

2. Installer [Docker Desktop](https://docs.docker.com/desktop/install/windows-install/) puis dans `Settings → Resources → WSL Integration` activer ta distro.

**Cloner et lancer — depuis le terminal WSL2 (pas PowerShell) :**
```bash
# Important : cloner dans WSL2, pas dans C:\
cd ~
git clone https://github.com/PierreGallardoPro/projet-zeroclaw.git
cd projet-zeroclaw
mkdir -p workspace && chmod 777 workspace
cp .env.example .env
# éditer .env
docker compose up -d --build
```

Le log viewer est accessible directement sur `http://localhost:8080` — pas de tunnel SSH nécessaire en local.

**Récupérer les fichiers générés par le code-agent :**
```powershell
# Depuis PowerShell — copier le workspace vers le bureau
scp -r user@IP_SERVEUR:~/projet-zeroclaw/workspace/ C:\Users\TonNom\Desktop\workspace
```

Ou ouvrir le dossier directement dans **VSCode** avec l'extension [Remote - SSH](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-ssh) — tu modifies `INSTRUCTIONS.md` et vois les fichiers générés apparaître en temps réel.

> **Note watchdog sur Windows/WSL2 :** la surveillance des fichiers peut avoir un délai de 1-2s comparé à Linux natif — sans impact sur le fonctionnement.

---

### 🍎 macOS (Docker Desktop)

Installer [Docker Desktop pour Mac](https://docs.docker.com/desktop/install/mac-install/), puis :

```bash
git clone https://github.com/PierreGallardoPro/projet-zeroclaw.git
cd projet-zeroclaw
mkdir -p workspace && chmod 777 workspace
cp .env.example .env
# éditer .env
docker compose up -d --build
```

Le log viewer est accessible directement sur `http://localhost:8080`.

---

## Agents

### 📬 mail-agent / mail-agent-gmail

Connexion IMAP → récupération des e-mails non lus → classification par Claude → déplacement dans le bon dossier. Cycle toutes les 15 minutes.

### 🤖 code-agent

Surveille `workspace/INSTRUCTIONS.md`. Dès qu'il est modifié, envoie l'instruction à Claude qui génère du code et l'écrit directement dans le workspace.

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

**Utilisation :**

1. Ouvre `workspace/INSTRUCTIONS.md`
2. Écris ton instruction, par exemple :
```
Crée une API Flask avec deux routes :
- GET /hello → retourne {"message": "Hello World"}
- GET /status → retourne {"status": "ok"}
```
3. Sauvegarde — l'agent réagit dans la seconde
4. Les fichiers générés apparaissent dans `workspace/`, la réponse complète dans `RESPONSE.md`

---

## Installation (serveur Linux)

```bash
git clone https://github.com/PierreGallardoPro/projet-zeroclaw.git
cd projet-zeroclaw
mkdir -p workspace && chown 1000:1000 workspace
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

```bash
docker compose up -d --build
```

---

## Commandes utiles

```bash
# Statut des conteneurs
docker compose ps

# Logs en temps réel
docker compose logs -f code-agent
docker compose logs -f mail-agent

# Rebuild après modification du code
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
- En production (serveur), le port `8080` est bindé sur `127.0.0.1` — inaccessible sans tunnel SSH

---

## Licence

MIT