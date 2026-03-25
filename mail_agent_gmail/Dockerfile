FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mail_agent.py .
COPY logger.py .          
RUN adduser --disabled-password --gecos "" appuser
USER appuser
CMD ["python", "mail_agent.py"]
