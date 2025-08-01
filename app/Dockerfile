FROM python:3.11-slim-bookworm

# Installer uniquement les libs système nécessaires à l'exécution
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
    pip install Pillow==10.0.1 && \
    pip install face-recognition-models==0.1.3

# Injecter dlib déjà compilé (venant du build local)
COPY dlib /usr/local/lib/python3.11/site-packages/dlib
COPY dlib-20.0.0.dist-info /usr/local/lib/python3.11/site-packages/dlib-20.0.0.dist-info
COPY _dlib_pybind11.cpython-311-x86_64-linux-gnu.so /usr/local/lib/python3.11/site-packages/

# Installer face_recognition depuis GitHub master (avec patch pour compatibilité)
RUN pip install --no-deps git+https://github.com/ageitgey/face_recognition.git@master

# Installer les autres packages Python
RUN pip install -r requirements.txt

# Copier le code source de l'application
COPY . .

# Créer les dossiers nécessaires
RUN mkdir -p static/uploads/selfies static/uploads/photos

# Rendre le script de démarrage exécutable
RUN chmod +x start.sh

# Exposer le port (Render utilisera la variable PORT)
EXPOSE 8000

# Utiliser le script de démarrage pour Render
CMD ["./start.sh"]
