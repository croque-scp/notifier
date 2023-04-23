FROM mcr.microsoft.com/devcontainers/python:0-3.9-bullseye

RUN apt-get install libxml2-dev libxslt-dev

RUN pip install poetry
RUN poetry config virtualenvs.create false