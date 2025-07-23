# Utiliser une image avec les dépendances pré-installées
FROM python:3.11-slim

# Installer les dépendances système minimales
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libblas3 \
    liblapack3 \
    libatlas-base-dev \
    libhdf5-103 \
    && rm -rf /var/lib/apt/lists/*

# Variables d'environnement pour optimiser la compilation
ENV DLIB_USE_CUDA=0
ENV USE_AVX_INSTRUCTIONS=1

WORKDIR /app

# Copier les fichiers de dépendances Python
COPY requirements.txt .

# Installer les dépendances Python avec des wheels pré-compilés
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir numpy==1.24.3 && \
    pip install --no-cache-dir opencv-python-headless==4.8.1.78 && \
    pip install --no-cache-dir https://github.com/sachadee/Dlib/raw/main/dlib-19.24.2-cp311-cp311-linux_x86_64.whl && \
    pip install --no-cache-dir face-recognition==1.3.0 && \
    pip install --no-cache-dir -r requirements.txt

# Copier le code source de l'application
COPY . .

# Créer les dossiers nécessaires
RUN mkdir -p static/uploads/selfies static/uploads/photos

# Exposer le port
EXPOSE 8000

# Commande de démarrage
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT:-8000}"]