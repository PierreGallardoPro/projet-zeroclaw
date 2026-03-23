FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY log_agent.py .

# Créer le dossier de rapports
RUN mkdir -p /reports

# Créer l'utilisateur non-root avec le même GID que le groupe docker du host (999)
# Cela permet d'accéder à /var/run/docker.sock sans être root
RUN addgroup --gid 989 docker_host 2>/dev/null || true \
    && adduser --disabled-password --no-create-home --gecos "" --ingroup docker_host agent \
    && chown -R agent:docker_host /app /reports

USER agent

CMD ["python", "-u", "log_agent.py"]
