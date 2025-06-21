FROM python:3.13 AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

ENV PIP_DEFAULT_TIMEOUT=100
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
ENV POETRY_VERSION=2.1.3

RUN pip install "poetry==$POETRY_VERSION"

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.in-project true
RUN poetry install --no-interaction --no-root


FROM base AS build

COPY . .

RUN poetry build


FROM base AS execute
ENV PATH=/app/.venv/bin:$PATH
COPY --from=build /app/dist .
COPY --from=build /app/.venv ./.venv
RUN ./.venv/bin/pip install *.whl
COPY ./config ./config
ENTRYPOINT ["python", "-m", "notifier"]


FROM base AS test
ENV PATH=/app/.venv/bin:$PATH
RUN apt-get update && apt-get install -y default-mysql-client
COPY conftest.py .
COPY config/ config/
COPY tests/ tests/
COPY notifier/ notifier/
ENTRYPOINT ["pytest", "-vvx"]


FROM amazon/aws-lambda-python:3.13 AS execute_lambda
COPY --from=build /app/dist ${LAMBDA_TASK_ROOT}
RUN pip install ${LAMBDA_TASK_ROOT}/*.whl
COPY ./config ${LAMBDA_TASK_ROOT}/config
ENV PATH=${LAMBDA_TASK_ROOT}/.venv/bin:$PATH
COPY ./lambda_function.py ${LAMBDA_TASK_ROOT}
CMD ["lambda_function.lambda_handler"]


FROM base AS typecheck
COPY . .
RUN poetry install --with dev
ENTRYPOINT ["poetry", "run", "mypy", "notifier", "tests"]