# Utiliser une image avec conda pour de meilleurs wheels pré-compilés
FROM continuumio/miniconda3:latest

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Variables d'environnement pour optimiser la compilation
ENV DLIB_USE_CUDA=0
ENV USE_AVX_INSTRUCTIONS=1

WORKDIR /app

# Copier les fichiers de dépendances Python
COPY requirements.txt .

# Installer les dépendances via conda et pip
RUN conda install -c conda-forge dlib=19.24.2 opencv=4.8.1 numpy=1.24.3 -y && \
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