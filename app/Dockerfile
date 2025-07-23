# Utiliser une image avec dlib et opencv pré-compilés
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

WORKDIR /app

# Copier les fichiers de dépendances Python
COPY requirements.txt .

# Installer d'abord les dépendances lourdes avec des versions spécifiques
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir numpy==1.24.3 && \
    pip install --no-cache-dir dlib==19.24.2 && \
    pip install --no-cache-dir opencv-python-headless==4.8.1.78 && \
    pip install --no-cache-dir face-recognition==1.3.0

# Installer le reste des dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source de l'application
COPY . .

# Créer les dossiers nécessaires
RUN mkdir -p static/uploads/selfies static/uploads/photos

# Exposer le port
EXPOSE 8000

# Commande de démarrage
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT:-8000}"]