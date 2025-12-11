FROM python:3.11-slim-bookworm

# Variables d'environnement utiles
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ONLY_BINARY=:all:

WORKDIR /app

# Installer uniquement les libs système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libatlas-base-dev \
    libpng-dev \
    libjpeg62-turbo \
    libwebp-dev \
    libwebp7 \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Copier uniquement les requirements pour profiter au max du cache
COPY requirements.txt ./requirements.txt

# Installer les dépendances Python "lourdes" et figées dans le même layer
RUN pip install --upgrade pip setuptools wheel \
 && pip install \
      numpy==1.24.3 \
      opencv-python-headless==4.8.1.78 \
      Pillow==10.0.1 \
      face-recognition-models==0.1.3 \
 && pip install --no-deps git+https://github.com/ageitgey/face_recognition.git@master \
 && pip install -r requirements.txt

# Copier le reste de l'application (c'est cette couche qui saute à chaque changement de code)
COPY . .

# Injecter dlib déjà compilé (si présent dans le repo)
RUN python - << 'PY'
import os, shutil, sys
site = sysconfig.get_paths()["purelib"] if (sys := __import__("sysconfig")) else "/usr/local/lib/python3.11/site-packages"
base = "/app"

mapping = [
    ("dlib", "dlib"),
    ("dlib-20.0.0.dist-info", "dlib-20.0.0.dist-info"),
    ("_dlib_pybind11.cpython-311-x86_64-linux-gnu.so", "_dlib_pybind11.cpython-311-x86_64-linux-gnu.so"),
]

for src, dest in mapping:
    src_path = os.path.join(base, src)
    dest_path = os.path.join(site, dest)
    if os.path.isdir(src_path):
        shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
    elif os.path.isfile(src_path):
        shutil.copy2(src_path, dest_path)
PY

# Créer les dossiers nécessaires + droits script start
RUN mkdir -p static/uploads/selfies static/uploads/photos \
    && chmod +x start.sh

EXPOSE 10000

CMD ["./start.sh"]
