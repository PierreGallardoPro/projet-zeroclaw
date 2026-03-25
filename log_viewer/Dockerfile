FROM python:3.12-alpine
WORKDIR /app
COPY log_viewer.py .
RUN adduser -D appuser
USER appuser
EXPOSE 8080
CMD ["python", "log_viewer.py"]