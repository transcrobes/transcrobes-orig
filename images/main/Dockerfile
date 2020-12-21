# vim:set ft=dockerfile
FROM python:3.9-slim

RUN apt update && apt install -y gcc git libmagic1 mime-support && apt -y autoremove && apt -y clean && rm -rf /var/lib/apt/lists/*

# Set environment varibles
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY ./src/requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY ./src /app
COPY ./scripts /app/scripts
COPY ./whitenoise /app/whitenoise

CMD ["/bin/bash", "/app/scripts/runserver.sh"]
