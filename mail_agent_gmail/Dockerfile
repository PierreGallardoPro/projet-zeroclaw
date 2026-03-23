FROM python:3.11-slim

WORKDIR /app

# Copier et installer les dépendances en premier (cache Docker optimisé)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY mail_agent.py .

# Créer un utilisateur non-root et lui donner accès au dossier
RUN adduser --disabled-password --no-create-home --gecos "" agent \
    && chown -R agent:agent /app

# Basculer sur l'utilisateur non-root
USER agent

CMD ["python", "-u", "mail_agent.py"]