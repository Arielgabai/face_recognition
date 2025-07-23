FROM python:3.11-slim-bullseye

# Installer uniquement les libs système nécessaires à l'exécution (pas à la compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libatlas-base-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV PIP_NO_CACHE_DIR=1
ENV PIP_ONLY_BINARY=:all:

WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt ./

# Injecter dlib déjà compilé (venant du build local)
COPY dlib /usr/local/lib/python3.11/site-packages/dlib
COPY dlib-20.0.0.dist-info /usr/local/lib/python3.11/site-packages/dlib-20.0.0.dist-info

# Installer les autres packages Python
RUN pip install --upgrade pip setuptools wheel && \
    pip install numpy==1.24.3 && \
    pip install opencv-python-headless==4.8.1.78 && \
    pip install face-recognition-models==0.1.3 && \
    pip install git+https://github.com/ageitgey/face_recognition.git@master && \
    pip install -r requirements.txt
# Copier le code source de l'application
COPY . .

# Créer les dossiers nécessaires
RUN mkdir -p static/uploads/selfies static/uploads/photos

# Exposer le port
EXPOSE 8000

# Démarrage de l’application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT:-8000}"]
