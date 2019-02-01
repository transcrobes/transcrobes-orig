# vim:set ft=dockerfile
FROM python:3.6-slim

RUN apt update && apt install -y portaudio19-dev gcc

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["/bin/bash", "/app/runserver.sh"]
