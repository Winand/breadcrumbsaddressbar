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
# https://doc.qt.io/qt-5/linux-requirements.html
# export QT_DEBUG_PLUGINS=1
RUN apt update && apt install -y libxrender1 libxcb-render0 libxcb-render-util0 \
    libxcb-shape0 libxcb-randr0 libxcb-xfixes0 libxcb-sync1 libxcb-shm0 \
    libxcb-icccm4 libxcb-keysyms1 libxcb-image0 libxkbcommon0 \
    libxkbcommon-x11-0 libfontconfig1 libfreetype6 libxext6 libx11-6 libxcb1 \
    libx11-xcb1 libsm6 libice6 libglibd-2.0-0
# Additional requirements
RUN apt install -y libgl1 libxcb-xinerama0 libdbus-1-3
# Qt6 QtGui requires libEGL.so.1, libxcb-cursor0 for Qt xcb platform plugin
RUN apt install -y libegl1 libxcb-cursor0
# qt.qpa.plugin: Could not load the Qt platform plugin "wayland" in "" even though it was found.
RUN apt install -y libwayland-egl1 libwayland-cursor0
###############################################################################

WORKDIR /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
# Create user with uid 1000 because /run/desktop/mnt/host/wslg/runtime-dir (XDG_RUNTIME_DIR)
# is mounted with that owner, see also https://github.com/microsoft/WSL/issues/9689
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
