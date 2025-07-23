FROM python:3.11-slim

RUN uname -m && python --version
# Étape 1 : Installer uniquement les libs nécessaires pour exécution (pas de build tools)
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
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /root/.cache

# Variables d'environnement
ENV DLIB_USE_CUDA=0
ENV USE_AVX_INSTRUCTIONS=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Étape 2 : Pré-copie du requirements uniquement (optimise le cache)
COPY requirements.txt ./

# Étape 3 : Installer d'abord les gros packages un par un pour meilleure gestion des erreurs
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir numpy==1.24.3 && \
    pip install --no-cache-dir opencv-python-headless==4.8.1.78 && \
    pip install --no-cache-dir https://github.com/sachadee/Dlib/raw/main/dlib-19.24.2-cp311-cp311-linux_x86_64.whl || (echo "⚠️ Erreur: dlib non installé – vérifie la compatibilité de la wheel avec l'image actuelle." && exit 1) && \
    pip install --no-cache-dir face-recognition==1.3.0 && \
    pip install --no-cache-dir -r requirements.txt

# Étape 4 : Copier le reste de l’application
COPY . .

# Étape 5 : Créer les dossiers nécessaires à l'exécution
RUN mkdir -p static/uploads/selfies static/uploads/photos

EXPOSE 8000

# Démarrage
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT:-8000}"]
