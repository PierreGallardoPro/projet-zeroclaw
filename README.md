# 🦾 projet-zeroclaw

Une plateforme d'**agents IA autonomes** modulaires, propulsée par **ZeroClaw**, **OmniRoute** et **Claude (Anthropic)** — le tout orchestré via Docker.

Chaque agent est indépendant et peut être activé ou désactivé sans impacter les autres.

---

## 📐 Architecture

```
projet-zeroclaw/
├── docker-compose.yml       # Orchestration de tous les services
├── .env                     # Variables d'environnement (non versionné)
├── .env.example             # Template des variables d'environnement
│
├── mail_agent/              # 📬 Agent de tri d'e-mails Gmail
│   ├── mail_agent.py
│   ├── requirements.txt
│   └── Dockerfile
│
└── mon_agent/               # 🤖 Ton prochain agent ici
    ├── agent.py
    ├── requirements.txt
    └── Dockerfile
```

### Services Docker socle

Ces deux services sont **partagés par tous les agents** — ils doivent toujours tourner.

| Service | Rôle | Port |
|---|---|---|
| `omniroute` | Routeur LLM — proxy les requêtes vers les providers IA | `20128` |
| `zeroclaw` | Gateway IA — gère les modèles et les accès | `42617` |

---

## 🤖 Agents disponibles

### 📬 mail_agent — Tri automatique des e-mails Gmail

Connecté à Gmail via IMAP, cet agent analyse les e-mails non lus et les classe automatiquement dans des dossiers intelligents grâce à Claude.

**Flux de données :**
```
Gmail (IMAP) ──▶ mail-agent ──▶ OmniRoute ──▶ Claude
                     │
                     └──▶ Crée des dossiers Gmail et y déplace les e-mails
```

**Fonctionnement :**
1. Connexion à Gmail via **IMAP SSL**
2. Récupération des e-mails **non lus** dans la boîte de réception
3. Envoi du sujet + extrait (500 caractères) à **Claude** via OmniRoute
4. Claude retourne un nom de dossier court (ex: `Factures`, `Newsletters`, `Projets`)
5. Création du dossier si inexistant, déplacement de l'e-mail
6. Cycle répété toutes les **15 minutes**

---

## ⚙️ Prérequis

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/)
- Un compte **Gmail** avec l'accès IMAP activé
- Un **mot de passe d'application Gmail** — [Créer ici](https://myaccount.google.com/apppasswords)
- Une clé API **OmniRoute**

---

## 🚀 Installation & Lancement

### 1. Cloner le dépôt

```bash
git clone https://github.com/PierreGallardoPro/projet-zeroclaw.git
cd projet-zeroclaw
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Édite `.env` :

```env
# Identifiants Gmail
GMAIL_USER=ton.email@gmail.com
GMAIL_APP_PASS=ton_mot_de_passe_application_de_16_lettres

# Configuration IA
OMNIROUTE_API_KEY=ta_cle_api_omniroute
AI_MODEL=kr/claude-sonnet-4.5
```

> ⚠️ **Ne commite jamais ton fichier `.env`** — il est listé dans le `.gitignore`.

### 3. Lancer tous les services

```bash
docker compose up -d --build
```

### 4. Lancer un agent spécifique uniquement

```bash
docker compose up -d omniroute zeroclaw mail-agent
```

### 5. Vérifier les logs

```bash
docker compose logs -f mail-agent
```

---

## ➕ Ajouter un nouvel agent

Le projet est conçu pour être **extensible**. Pour ajouter un agent :

1. **Créer un dossier** pour le nouvel agent :
```
projet-zeroclaw/
└── mon_agent/
    ├── agent.py
    ├── requirements.txt
    └── Dockerfile
```

2. **Ajouter le service** dans `docker-compose.yml` :
```yaml
mon-agent:
  build: ./mon_agent
  container_name: mon_agent
  restart: unless-stopped
  env_file:
    - .env
  environment:
    - OMNIROUTE_URL=http://omniroute:20128/v1/chat/completions
  depends_on:
    - omniroute
```

3. **Relancer** Docker Compose :
```bash
docker compose up -d --build mon-agent
```

Chaque agent communique avec Claude via OmniRoute sur le réseau Docker interne — aucune configuration réseau supplémentaire n'est nécessaire.

---

## 🛑 Arrêter les services

```bash
# Arrêter tous les services
docker compose down

# Arrêter un agent spécifique
docker compose stop mail-agent

# Supprimer aussi les volumes
docker compose down -v
```

---

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésite pas à ouvrir une *issue* ou une *pull request*.

---

## 📄 Licence

Ce projet est sous licence **MIT**.