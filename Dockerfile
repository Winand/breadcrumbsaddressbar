FROM ghcr.io/astral-sh/uv:0.6.2 AS uv
COPY pyproject.toml uv.lock /

# For more information, please refer to https://aka.ms/vscode-docker-python
# FROM python:slim
FROM python:3.12-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

###############################################################################
# Requirements: https://doc.qt.io/qt-5/linux-requirements.html | https://doc.qt.io/qt-6/linux-requirements.html
# Additional libraries for Qt5: libxcb-xinerama0 libxcursor1
# Check module load: ldd $(python -c "from PySide6 import QtWidgets as m; print(m.__file__)")
# Check Qt plugins load: QT_DEBUG_PLUGINS=1
# Check all libs: find /usr/local/lib/python3.12/site-packages/PySide6 -type f -executable ! -name "*.py" ! -path "*/scripts/*" | xargs -I {} sh -c 'echo {}; ldd "{}" | grep "not found"'
# Force Wayland or XCB: QT_QPA_PLATFORM=wayland | wayland-egl | xcb
RUN apt update && apt install -y \
  libgl1 \
  libxkbcommon0 \
  libegl1 \
  libfontconfig1 \
  libglib2.0-0 \
  libdbus-1-3 \
  libxcb-cursor0 \
  libxkbcommon-x11-0 \
  libxcb-icccm4 \
  libxcb-keysyms1 \
  libxcb-shape0 \
  libwayland-cursor0 \
  libatomic1 \
  libwayland-egl1 \
  libxrender1 \
  libice6 \
  libsm6 \
  && rm -rf /var/lib/apt/lists/*

###############################################################################

WORKDIR /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
#
# Wayland requires $XDG_RUNTIME_DIR to be accessible for current user, so create
# user with uid 1000 because /run/desktop/mnt/host/wslg/runtime-dir ($XDG_RUNTIME_DIR)
# is mounted with that uid, see also https://github.com/microsoft/WSL/issues/9689
RUN adduser -u 1000 --disabled-password --gecos "" appuser && chown -R appuser /app

# Install project dependencies
# https://docs.astral.sh/uv/concepts/python-versions/#disabling-automatic-python-downloads
ENV UV_PYTHON_DOWNLOADS=never
# for uv sync https://docs.astral.sh/uv/concepts/projects/config/#project-environment-path
ENV UV_PROJECT_ENVIRONMENT=/usr/local
# Do not buffer stdout/stderr https://stackoverflow.com/a/59812588
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=from=uv,source=/pyproject.toml,target=/app/pyproject.toml \
    --mount=from=uv,source=/uv.lock,target=/app/uv.lock \
  # Install dependencies from an existing uv.lock: uv sync --frozen
  uv sync --frozen --no-cache --no-install-project

# Install project in a separate layer for faster rebuilds
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=target=/app,type=bind,source=. \
  cd /app && \
  uv sync --frozen --no-cache

USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "breadcrumbsaddressbar\breadcrumbsaddressbar.py"]
