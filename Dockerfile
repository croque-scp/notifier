FROM python:3.13 AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project --no-dev


FROM base AS build

COPY . .

RUN uv build


FROM base AS execute
ENV PATH=/app/.venv/bin:$PATH
COPY --from=build /app/.venv ./.venv
COPY --from=build /app/dist .
RUN uv pip install --no-deps *.whl
COPY ./config ./config
ENTRYPOINT ["python", "-m", "notifier"]


FROM base AS test
ENV PATH=/app/.venv/bin:$PATH
RUN uv sync --frozen --no-install-project
RUN apt-get update && apt-get install -y default-mysql-client
COPY conftest.py .
COPY config/ config/
COPY tests/ tests/
COPY notifier/ notifier/
ENTRYPOINT ["pytest", "-vvx"]


FROM amazon/aws-lambda-python:3.13 AS execute_lambda
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-emit-project > requirements.txt && \
    uv pip install --system --no-cache -r requirements.txt
COPY --from=build /app/dist ${LAMBDA_TASK_ROOT}
RUN uv pip install --system --no-cache --no-deps ${LAMBDA_TASK_ROOT}/*.whl
COPY ./config ${LAMBDA_TASK_ROOT}/config
COPY ./lambda_function.py ${LAMBDA_TASK_ROOT}
CMD ["lambda_function.lambda_handler"]


FROM base AS typecheck
COPY . .
RUN uv sync --frozen
ENTRYPOINT ["uv", "run", "mypy", "notifier", "tests"]
