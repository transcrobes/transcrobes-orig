# vim:set ft=dockerfile
FROM python:3.6-slim

RUN apt update && apt install -y portaudio19-dev gcc git && apt -y autoremove && apt -y clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt

CMD ["/bin/bash", "/app/runserver.sh"]
