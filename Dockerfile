################################
# Base
# Sets up all our shared environment variables
################################
FROM python:3.10-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.7.0 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"

# prepend poetry and venv to path
ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"


################################
# App Builder
# Used to build deps + create our virtual environment
################################
FROM base AS app-builder

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
    && apt-get clean

# install poetry - respects $POETRY_VERSION & $POETRY_HOME
# The --mount will mount the buildx cache directory to where
# Poetry and Pip store their cache so that they can re-use it
RUN --mount=type=cache,target=/root/.cache \
    curl -sSL https://install.python-poetry.org | python3 -

# copy project requirement files here to ensure they will be cached.
WORKDIR $PYSETUP_PATH
COPY poetry.lock pyproject.toml ./

# install runtime deps - uses $POETRY_VIRTUALENVS_IN_PROJECT internally
RUN --mount=type=cache,target=/root/.cache \
    poetry install --sync --no-root


################################
# App
# App runtime, that runs once in a while
################################
FROM base AS app

# Environment variables
ENV FEED_URLS=""
ENV OPENAI_API_KEY=""
ENV BATCH_SIZE="100"

COPY --from=app-builder $PYSETUP_PATH $PYSETUP_PATH
COPY . /app/

WORKDIR /app
VOLUME /app/rss

CMD ["bash", "scripts/run-app.sh"]


################################
# RSS web server
# Web server for RSS feed
################################
FROM nginx:stable-alpine AS web-server

WORKDIR /app
VOLUME /app/rss

COPY nginx.conf /etc/nginx/nginx.conf
