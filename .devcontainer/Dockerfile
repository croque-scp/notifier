FROM mcr.microsoft.com/devcontainers/python:0-3.8-bullseye

RUN apt-get install libxml2-dev libxslt-dev

RUN pip install poetry
RUN poetry config virtualenvs.in-project true