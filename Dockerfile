# For more information, please refer to https://aka.ms/vscode-docker-python
# FROM python:slim
FROM python:3.9-slim

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
###############################################################################

# Install pip requirements
# https://stackoverflow.com/q/3664478/optional-dependencies-in-a-pip-requirements-file
COPY requirements.txt requirements-dev.txt ./
RUN python -m pip install -r requirements.txt
RUN python -m pip install -r requirements-dev.txt

WORKDIR /app
COPY . /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python", "breadcrumbsaddressbar\breadcrumbsaddressbar.py"]
