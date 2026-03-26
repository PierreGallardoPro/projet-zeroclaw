FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY code_agent.py .
COPY logger.py .
RUN adduser --disabled-password --no-create-home --gecos "" agent \
    && mkdir -p /app/logs /app/workspace \
    && chown -R agent:agent /app
USER agent
CMD ["python", "code_agent.py"]
