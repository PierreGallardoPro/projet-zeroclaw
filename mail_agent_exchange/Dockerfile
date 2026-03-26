FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mail_agent_exchange.py .
COPY logger.py .
RUN adduser --disabled-password --no-create-home --gecos "" agent \
    && mkdir -p /app/logs \
    && chown -R agent:agent /app
USER agent
CMD ["python", "mail_agent_exchange.py"]
