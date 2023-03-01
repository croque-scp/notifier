FROM python:3.8-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app


FROM base as build

ENV PIP_DEFAULT_TIMEOUT=100
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
ENV POETRY_VERSION=1.3.2

RUN pip install "poetry==$POETRY_VERSION"

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.in-project true
RUN poetry install --no-interaction --no-root

COPY . .

RUN poetry build


FROM base AS execute
COPY --from=build /app/dist .
COPY --from=build /app/.venv ./.venv
RUN ./.venv/bin/pip install *.whl
COPY ./config ./config
ENV PATH=/app/.venv/bin:$PATH
ENTRYPOINT ["python", "-m", "notifier"]


FROM execute AS test
RUN apt-get update && apt-get install -y default-mysql-client
ENV PATH=/app/.venv/bin:$PATH
COPY conftest.py .
COPY tests/ tests/
ENTRYPOINT ["pytest", "-x"]


FROM public.ecr.aws/lambda/python:3.8 AS execute_lambda
COPY --from=build /app/dist ${LAMBDA_TASK_ROOT}
RUN pip install ${LAMBDA_TASK_ROOT}/*.whl
COPY ./config ${LAMBDA_TASK_ROOT}/config
ENV PATH=${LAMBDA_TASK_ROOT}/.venv/bin:$PATH
COPY ./lambda_function.py ${LAMBDA_TASK_ROOT}
CMD ["lambda_function.lambda_handler"]