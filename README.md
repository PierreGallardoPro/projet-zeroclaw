# 🦾 projet-zeroclaw

![Logo](./src/images/logo_projetzeroclaw.png)

Plateforme d'**agents IA autonomes** propulsée par **ZeroClaw**, **OmniRoute** et **Claude (Anthropic)** — orchestrée via Docker.

> Compatible Linux · macOS · Windows (WSL2)

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
├── mail_agent_gmail/         # Agent de tri — boîte Gmail
├── code_agent/               # Agent de codage autonome
└── log_viewer/               # Interface web de visualisation des logs
```

Chaque dossier agent contient : `agent.py`, `logger.py`, `requirements.txt`, `Dockerfile`.

### Services

| Service | Rôle | Port |
|---|---|---|
| `omniroute` | Routeur LLM | `20128` |
| `zeroclaw` | Gateway IA | `42617` |
| `mail-agent` | Tri e-mails OVH / IMAP | — |
| `mail-agent-gmail` | Tri e-mails Gmail | — |
| `code-agent` | Génère du code depuis des instructions | — |
| `log-viewer` | Interface web des logs | `8080` |

---

## Installation

```bash
git clone https://github.com/PierreGallardoPro/projet-zeroclaw.git
cd projet-zeroclaw
mkdir -p workspace && chown 1000:1000 workspace
cp .env.example .env
# éditer .env
docker compose up -d --build
```

### Variables d'environnement

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

> Pour Gmail : générer un mot de passe d'application sur [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

---

## Agents

### 📬 mail-agent / mail-agent-gmail

Connexion IMAP → récupération des e-mails non lus → classification par Claude → déplacement dans le bon dossier. Cycle toutes les **15 minutes**.

### 🤖 code-agent

Surveille `workspace/INSTRUCTIONS.md`. Dès qu'il est modifié, envoie l'instruction à Claude qui génère du code et l'écrit dans le workspace.

1. Ouvre `workspace/INSTRUCTIONS.md`
2. Écris ton instruction et sauvegarde
3. Les fichiers générés apparaissent dans `workspace/`
4. La réponse complète est dans `workspace/RESPONSE.md`

---

## Logs

Accessible via tunnel SSH :

```bash
ssh -N -L 8080:127.0.0.1:8080 user@IP_SERVEUR
```

Puis ouvrir `http://localhost:8080`.

---

## Commandes utiles

```bash
docker compose ps                          # statut
docker compose logs -f <service>           # logs temps réel
docker compose up -d --build <service>     # rebuild un agent
docker compose down                        # tout arrêter
```

---

## Ajouter un agent

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

3. `docker compose up -d --build mon-agent`

---

## Sécurité

- `.env` en `chmod 600`
- Variables sensibles uniquement via `env_file`, jamais sous `environment:`
- Port `8080` bindé sur `127.0.0.1` — accessible uniquement via tunnel SSH

---

## Licence

MIT