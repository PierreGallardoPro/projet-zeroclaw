# 🦾 projet-zeroclaw

Un agent IA autonome qui trie automatiquement tes e-mails Gmail en dossiers intelligents, propulsé par **ZeroClaw**, **OmniRoute** et **Claude (Anthropic)** — le tout orchestré via Docker.

---

## 📐 Architecture

```
projet-zeroclaw/
├── docker-compose.yml       # Orchestration des 3 services
├── .env                     # Variables d'environnement (non versionné)
└── mail_agent/
    ├── mail_agent.py        # Agent Python de tri d'e-mails
    ├── requirements.txt     # Dépendances Python
    └── Dockerfile           # Image du mail agent
```

### Services Docker

| Service | Rôle | Port |
|---|---|---|
| `omniroute` | Routeur LLM — proxy les requêtes vers les providers IA | `20128` |
| `zeroclaw` | Gateway IA — gère les modèles et les accès | `42617` |
| `mail-agent` | Agent Python — se connecte à Gmail et classe les e-mails | — |

**Flux de données :**
```
Gmail (IMAP) ──▶ mail-agent ──▶ OmniRoute ──▶ Claude (via ZeroClaw)
                     │
                     └──▶ Crée des dossiers Gmail et y déplace les e-mails
```

---

## ⚙️ Prérequis

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/)
- Un compte **Gmail** avec l'accès IMAP activé
- Un **mot de passe d'application Gmail** (pas ton mot de passe principal) — [Créer ici](https://myaccount.google.com/apppasswords)
- Une clé API **OmniRoute**

---

## 🚀 Installation & Lancement

### 1. Cloner le dépôt

```bash
git clone https://github.com/PierreGallardoPro/projet-zeroclaw.git
cd projet-zeroclaw
```

### 2. Configurer les variables d'environnement

Copie le fichier d'exemple et remplis tes valeurs :

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

### 3. Lancer les services

```bash
docker compose up -d --build
```

### 4. Vérifier que tout tourne

```bash
docker compose ps
docker compose logs -f mail-agent
```

---

## 🔁 Fonctionnement

L'agent Python (`mail_agent.py`) tourne en boucle et effectue un cycle toutes les **15 minutes** :

1. Connexion à Gmail via **IMAP SSL**
2. Récupération des e-mails **non lus** dans la boîte de réception
3. Envoi du sujet + extrait (500 caractères) à **Claude** via OmniRoute
4. Claude retourne un nom de dossier court (ex: `Factures`, `Newsletters`, `Projets`)
5. Création du dossier si inexistant, déplacement de l'e-mail
6. Répétition au prochain cycle

---

## 🛑 Arrêter les services

```bash
docker compose down
```

Pour supprimer aussi les volumes :

```bash
docker compose down -v
```

---

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésite pas à ouvrir une *issue* ou une *pull request*.

---

## 📄 Licence

Ce projet est sous licence **MIT**.