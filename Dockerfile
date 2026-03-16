FROM python:3.13

RUN mkdir /app/
WORKDIR /app

COPY src/Batteryservice src/Batteryservice
COPY pyproject.toml ./
COPY README.md ./
RUN pip install ./

ENTRYPOINT python3 src/Batteryservice/batteryservice.py