# Guide de Déploiement - Face Recognition App

## Problèmes Résolus

### 1. Conflit NumPy/OpenCV
- **Problème** : `_ARRAY_API not found` et `numpy.core.multiarray failed to import`
- **Solution** : Versions spécifiques dans `requirements.txt` et ordre d'installation optimisé

### 2. Dépendances Manquantes
- **Problème** : Versions non spécifiées causant des incompatibilités
- **Solution** : Versions exactes pour NumPy, OpenCV et face_recognition

## Structure du Projet

```
app/
├── main.py                 # Application FastAPI principale
├── face_recognizer.py      # Module de reconnaissance faciale
├── models.py              # Modèles de base de données
├── database.py            # Configuration de la base de données
├── auth.py                # Authentification
├── schemas.py             # Schémas Pydantic
├── requirements.txt       # Dépendances Python
├── Dockerfile            # Configuration Docker
├── docker-compose.yml    # Orchestration Docker
├── start.sh              # Script de démarrage
├── test_imports.py       # Test des importations
└── static/               # Fichiers statiques
    ├── uploads/
    │   ├── selfies/
    │   └── photos/
    └── *.html
```

## Déploiement

### Option 1 : Docker (Recommandé)

```bash
# Construire et démarrer
docker-compose up --build

# Vérifier les logs
docker-compose logs -f

# Arrêter
docker-compose down
```

### Option 2 : Déploiement Local

```bash
# Installer les dépendances
pip install -r requirements.txt

# Tester les importations
python test_imports.py

# Démarrer l'application
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Option 3 : Déploiement Cloud (Render, Heroku, etc.)

1. **Préparer les fichiers** :
   - `requirements.txt` ✅ (versions spécifiques)
   - `Dockerfile` ✅ (optimisé)
   - `start.sh` ✅ (script de démarrage)

2. **Variables d'environnement** :
   ```bash
   PORT=8000
   DATABASE_URL=sqlite:///./face_recognition.db
   ```

3. **Déployer** :
   - Connecter le repository Git
   - Configurer les variables d'environnement
   - Déployer automatiquement

## Vérification

### Test des Importations
```bash
python test_imports.py
```

### Test de l'API
```bash
curl http://localhost:8000/api
```

### Test de l'Interface Web
```bash
curl http://localhost:8000/
```

## Dépannage

### Erreur NumPy/OpenCV
```bash
# Réinstaller avec des versions spécifiques
pip uninstall numpy opencv-python
pip install numpy==1.24.3 opencv-python-headless==4.8.1.78
```

### Erreur face_recognition
```bash
# Réinstaller face_recognition
pip uninstall face_recognition
pip install --no-deps git+https://github.com/ageitgey/face_recognition.git@master
```

### Erreur de Port
```bash
# Vérifier le port utilisé
netstat -tulpn | grep 8000
# ou
lsof -i :8000
```

## Logs et Debug

### Docker Logs
```bash
docker-compose logs -f app
```

### Logs Locaux
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug
```

## Performance

- **Mémoire** : Limite à 2GB pour éviter les problèmes
- **CPU** : Optimisé pour les calculs de reconnaissance faciale
- **Stockage** : Volumes persistants pour les uploads

## Sécurité

- **CORS** : Configuré pour les domaines autorisés
- **Authentification** : JWT tokens
- **Uploads** : Validation des types de fichiers
- **Base de données** : SQLite pour la simplicité

## Support

En cas de problème :
1. Vérifier les logs : `docker-compose logs -f`
2. Tester les importations : `python test_imports.py`
3. Vérifier les versions : `pip list | grep -E "(numpy|opencv|face)"` 