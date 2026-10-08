# Linux development image for base_infrastructure (VS Code Dev Container, "app" service).
#
#   Debian 12 (bookworm) + Python 3.13 (same minor version as the Windows .venv)
#   + Microsoft ODBC Driver 18 for SQL Server (pyodbc / SQLAlchemy mssql+pyodbc)
#   + the pinned project dependencies in /opt/venv (requirements.txt, requirements-dev.txt)
#
# Build context: the repository root (see docker-compose.yml). Only the requirements files
# are sent (.devcontainer/Dockerfile.dockerignore); the source code is bind-mounted at run time.
FROM python:3.13-slim-bookworm

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=1000
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

# --- system packages -----------------------------------------------------------------------
#  git, openssh-client, sudo, procps, less ...  developer tooling
#  build-essential, pkg-config               compile sdists that have no wheel (safety net)
#  unixodbc, unixodbc-dev                     ODBC driver manager needed by pyodbc
#  libgomp1                                   OpenMP runtime of lightgbm / xgboost wheels
#  libgl1, libglib2.0-0, libdbus-1-3,
#  libxkbcommon0, libfontconfig1              shared libraries PyQt5 needs at import time
#  curl, gnupg, ca-certificates               add the Microsoft package repository
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        git openssh-client sudo procps less nano curl gnupg ca-certificates \
        build-essential pkg-config \
        unixodbc unixodbc-dev \
        libgomp1 \
        libgl1 libglib2.0-0 libdbus-1-3 libxkbcommon0 libfontconfig1 \
 && rm -rf /var/lib/apt/lists/*

# --- Microsoft ODBC Driver 18 + sqlcmd (mssql-tools18) --------------------------------------
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
 && echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/microsoft-prod.list \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 mssql-tools18 \
 && rm -rf /var/lib/apt/lists/*
ENV PATH="/opt/mssql-tools18/bin:${PATH}"

# --- non-root user (UID/GID are remapped to the host user by VS Code if needed) -------------
RUN groupadd --gid ${USER_GID} ${USERNAME} \
 && useradd --uid ${USER_UID} --gid ${USER_GID} -m -s /bin/bash ${USERNAME} \
 && echo "${USERNAME} ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} \
 && chmod 0440 /etc/sudoers.d/${USERNAME}

# --- Python dependencies (virtualenv owned by the dev user, so `pip install` works) ---------
RUN python -m venv /opt/venv && chown -R ${USERNAME}:${USERNAME} /opt/venv
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"
USER ${USERNAME}
COPY --chown=${USERNAME}:${USERNAME} requirements.txt requirements-dev.txt /tmp/requirements/
# CPU builds of the pinned torch stack first (the PyPI Linux wheels pull ~3 GB of CUDA libraries
# that cannot be used in this container); requirements.txt then finds them already satisfied and
# installs their dependencies at the pinned versions (--no-deps here; `pip check` verifies).
RUN pip install --upgrade pip==25.2 \
 && pip install --no-deps --index-url https://download.pytorch.org/whl/cpu \
        torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 \
 && pip install -r /tmp/requirements/requirements-dev.txt \
 && pip check

WORKDIR /workspaces/base_infrastructure
CMD ["sleep", "infinity"]
