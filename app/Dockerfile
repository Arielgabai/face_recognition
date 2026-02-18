FROM python:3.11-slim-bookworm

# Installer uniquement les libs système nécessaires à l'exécution
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libpng-dev \
    libjpeg62-turbo \
    libwebp-dev \
    libwebp7 \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

ENV PIP_NO_CACHE_DIR=1
ENV PIP_ONLY_BINARY=:all:

WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt ./

# Installer d'abord NumPy, OpenCV et Pillow avec des versions spécifiques
RUN pip install --upgrade pip setuptools wheel && \
    pip install numpy==1.24.3 && \
    pip install opencv-python-headless==4.8.1.78 && \
    pip install Pillow==10.0.1

# Installer les autres packages Python
RUN pip install -r requirements.txt

# Copier le code source de l'application
COPY . .

# Rester sur les pages statiques servies par FastAPI

# Créer les dossiers nécessaires
RUN mkdir -p static/uploads/selfies static/uploads/photos

# Convertir les fins de ligne Windows (CRLF) vers Linux (LF) et rendre exécutable
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

# Exposer le port (Render utilisera la variable PORT)
EXPOSE 10000

# Utiliser le script de démarrage pour Render
CMD ["/bin/bash", "./start.sh"]
