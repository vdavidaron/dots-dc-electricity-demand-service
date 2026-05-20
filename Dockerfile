FROM python:3.13-slim

WORKDIR /app

COPY src/Batteryservice src/Batteryservice
COPY pyproject.toml ./
COPY README.md ./

RUN pip install --no-cache-dir ./

ENTRYPOINT ["python3", "src/Batteryservice/batteryservice.py"]