FROM mcr.microsoft.com/devcontainers/python:3.13

RUN apt-get install libxml2-dev libxslt-dev

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
