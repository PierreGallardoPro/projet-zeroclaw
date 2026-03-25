FROM python:3.11-slim

# Éviter la mise en buffer de Python pour voir les logs en temps réel
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Installation des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie des scripts de l'agent
COPY . .

# Lancement de l'agent
CMD ["python", "agent.py"]