# 🦾 Agent Autonome via ZeroClaw - projet-zeroclaw

Une plateforme d'**agents IA autonomes** modulaires, propulsée par **ZeroClaw**, **OmniRoute** et **Claude (Anthropic)** — le tout orchestré via Docker.

Chaque agent est indépendant et peut être activé ou désactivé sans impacter les autres.

---

## 📐 Architecture

```
projet-zeroclaw/
├── docker-compose.yml         # Orchestration de tous les services
├── .env                       # Variables d'environnement (non versionné)
├── .env.example               # Template des variables d'environnement
│
├── mail_agent/                # 📬 Agent de tri — boîte OVH (ou tout fournisseur IMAP)
│   ├── mail_agent.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── mail_agent_gmail/          # 📬 Agent de tri — boîte Gmail
│   ├── mail_agent.py
│   ├── requirements.txt
│   └── Dockerfile
│
└── mon_agent/                 # 🤖 Ton prochain agent ici
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

### Flux complet de l'architecture

```
Boîte mail ──▶ mail-agent ──▶ OmniRoute ──▶ ZeroClaw ──▶ Claude
                    └──▶ Classe l'e-mail dans le bon dossier
```

---

## 🤖 Agents disponibles

### 📬 mail_agent — Tri automatique (OVH / multi-fournisseurs)

Connecté à n'importe quelle boîte mail via IMAP, cet agent analyse les e-mails non lus et les classe automatiquement dans des dossiers intelligents grâce à Claude.

**Fournisseurs supportés :**

| Fournisseur | `IMAP_HOST` | `IMAP_PORT` |
|---|---|---|
| OVH | `ssl0.ovh.net` | `993` |
| Gmail | `imap.gmail.com` | `993` |
| Outlook / Hotmail | `outlook.office365.com` | `993` |
| Yahoo | `imap.mail.yahoo.com` | `993` |
| Infomaniak | `mail.infomaniak.com` | `993` |

**Flux de données :**
```
Boîte mail (IMAP) ──▶ mail-agent ──▶ OmniRoute ──▶ Claude
                           │
                           └──▶ Crée des dossiers et y déplace les e-mails
```

**Fonctionnement :**
1. Connexion au serveur IMAP via SSL
2. Récupération des e-mails **non lus** dans la boîte de réception
3. Envoi du sujet + extrait (500 caractères) à **Claude** via OmniRoute
4. Claude retourne un nom de dossier court (ex: `Factures`, `Newsletters`, `Projets`)
5. Création du dossier si inexistant, déplacement de l'e-mail
6. Cycle répété toutes les **15 minutes**

---

### 📬 mail_agent_gmail — Tri automatique (Gmail)

Version dédiée Gmail utilisant le système de **mot de passe d'application** Google.

> Nécessite d'activer l'accès IMAP dans les paramètres Gmail et de générer un mot de passe d'application sur [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).

---

## ⚙️ Prérequis

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/)
- Un compte mail avec accès IMAP activé
- Une clé API **OmniRoute**
- Pour Gmail : un **mot de passe d'application** Google (pas le mot de passe principal)

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
# ── Boîte OVH (mail_agent) ──────────────────────────
MAIL_USER=ton.email@tondomaine.com
MAIL_PASS=ton_mot_de_passe_ovh
IMAP_HOST=ssl0.ovh.net
IMAP_PORT=993

# ── Boîte Gmail (mail_agent_gmail) ──────────────────
GMAIL_USER=ton.email@gmail.com
GMAIL_APP_PASS=ton_mot_de_passe_app_google

# ── Configuration IA ─────────────────────────────────
OMNIROUTE_API_KEY=ta_cle_api_omniroute
AI_MODEL=kr/claude-sonnet-4.5
```

> ⚠️ **Ne commite jamais ton fichier `.env`** — il est listé dans le `.gitignore`.

### 3. Protéger le fichier `.env` sur le serveur

```bash
chmod 600 .env
chown root:root .env
```

### 4. Lancer tous les services

```bash
docker compose up -d --build
```

### 5. Lancer un agent spécifique uniquement

```bash
# Socle + agent OVH uniquement
docker compose up -d omniroute zeroclaw mail-agent

# Socle + agent Gmail uniquement
docker compose up -d omniroute zeroclaw mail-agent-gmail
```

### 6. Vérifier les logs

```bash
docker compose logs -f mail-agent
docker compose logs -f mail-agent-gmail
```

---

## 🔄 Mettre à jour le projet

Les mises à jour se font via `git pull` directement depuis le serveur, suivi d'un rebuild des conteneurs modifiés.

### Mise à jour complète (tous les services)

```bash
cd /home/pierregallardo/projet-zeroclaw

# 1. Récupérer les dernières modifications depuis GitHub
git pull origin main

# 2. Rebuilder et relancer tous les conteneurs
docker compose up -d --build
```

### Mise à jour d'un agent spécifique uniquement

Si seul le code d'un agent a changé, inutile de tout rebuilder :

```bash
cd /home/pierregallardo/projet-zeroclaw

# 1. Récupérer les modifications
git pull origin main

# 2. Rebuilder et relancer uniquement l'agent concerné
docker compose up -d --build mail-agent
# ou
docker compose up -d --build mail-agent-gmail
```

### Mise à jour du docker-compose.yml uniquement

Si seul le fichier `docker-compose.yml` a changé (ajout d'un service, variable d'env…) sans modification de code, pas besoin de rebuild :

```bash
git pull origin main
docker compose up -d
```

### Vérifier que tout est reparti correctement

```bash
# Statut de tous les conteneurs
docker compose ps

# Logs en temps réel
docker compose logs -f
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

3. **Pousser sur GitHub et déployer** :
```bash
git add .
git commit -m "feat: ajout de mon_agent"
git push origin main

# Sur le serveur
git pull origin main
docker compose up -d --build mon-agent
```

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

## 🔒 Sécurité

- Le fichier `.env` doit être en `chmod 600` et appartenir à `root`
- Ne jamais déclarer les variables sensibles sous la clé `environment:` dans `docker-compose.yml` (elles apparaissent en clair dans `docker inspect`) — utiliser uniquement `env_file`

---

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésite pas à ouvrir une *issue* ou une *pull request*.

---

## 📄 Licence

Ce projet est sous licence **MIT**.