FROM python:3.12-slim
WORKDIR /app
COPY log_viewer.py .
RUN adduser --disabled-password --no-create-home --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser
EXPOSE 8080
CMD ["python", "log_viewer.py"]
