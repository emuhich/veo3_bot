FROM python:3.10-buster

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


WORKDIR /usr/src/app/tg_bot

COPY requirements.txt /usr/src/app/tg_bot
RUN pip install -r /usr/src/app/tg_bot/requirements.txt
COPY . /usr/src/app/tg_bot