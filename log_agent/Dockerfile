FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY log_agent.py .

# Créer le dossier de rapports
RUN mkdir -p /reports

# Utilisateur non-root
RUN adduser --disabled-password --no-create-home --gecos "" agent \
    && chown -R agent:agent /app /reports

USER agent

CMD ["python", "-u", "log_agent.py"]