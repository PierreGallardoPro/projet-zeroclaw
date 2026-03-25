FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mail_agent.py .
COPY logger.py .
RUN adduser --disabled-password --no-create-home --gecos "" agent \
    && chown -R agent:agent /app
USER agent
CMD ["python", "mail_agent.py"]