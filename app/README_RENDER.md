# Guide de Déploiement sur Render

## Configuration Spécifique à Render

### Variables d'Environnement Requises

Dans votre dashboard Render, configurez ces variables :

```bash
PORT=8000
DATABASE_URL=sqlite:///./face_recognition.db
SECRET_KEY=votre-clé-secrète-changez-en-production
```

### Configuration du Service

1. **Type de Service** : Web Service
2. **Build Command** : `pip install -r requirements.txt`
3. **Start Command** : `./start.sh`
4. **Plan** : Free (pour commencer)

### Fichiers Requis

✅ **Dockerfile** : Optimisé pour Render
✅ **requirements.txt** : Versions spécifiques
✅ **start.sh** : Script de démarrage
✅ **test_imports.py** : Test des importations

## Déploiement

### Étape 1 : Préparer le Repository

```bash
# Vérifier que tous les fichiers sont présents
ls -la app/
# Doit contenir : Dockerfile, requirements.txt, start.sh, main.py, etc.
```

### Étape 2 : Connecter à Render

1. Allez sur [render.com](https://render.com)
2. Cliquez sur "New Web Service"
3. Connectez votre repository Git
4. Sélectionnez le dossier `app/`

### Étape 3 : Configuration

```yaml
# Configuration Render
Name: face-recognition-app
Environment: Docker
Region: Frankfurt (EU Central)
Branch: main
Root Directory: app
```

### Étape 4 : Variables d'Environnement

```bash
PORT=8000
DATABASE_URL=sqlite:///./face_recognition.db
SECRET_KEY=your-secret-key-change-in-production
```

## Vérification du Déploiement

### 1. Logs de Build

```bash
# Dans les logs Render, vous devriez voir :
✓ NumPy importé avec succès
✓ OpenCV importé avec succès
✓ face_recognition importé avec succès
✓ FastAPI importé avec succès
🎉 Toutes les importations fonctionnent correctement!
```

### 2. Test de l'API

```bash
# Votre URL Render sera : https://votre-app.onrender.com
curl https://votre-app.onrender.com/api
# Réponse attendue : {"message": "Face Recognition API"}
```

### 3. Test de l'Interface

```bash
curl https://votre-app.onrender.com/
# Doit retourner la page HTML
```

## Dépannage Render

### Erreur de Build

```bash
# Vérifier les logs de build
# Problème courant : timeout lors de l'installation de face_recognition
# Solution : Le Dockerfile est optimisé pour éviter cela
```

### Erreur de Démarrage

```bash
# Vérifier les logs de runtime
# Problème courant : PORT non défini
# Solution : Variable PORT=8000 dans Render
```

### Erreur NumPy/OpenCV

```bash
# Les versions spécifiques dans requirements.txt résolvent cela
numpy==1.24.3
opencv-python-headless==4.8.1.78
```

## Optimisations Render

### Performance

- **Mémoire** : Limite à 512MB sur le plan gratuit
- **CPU** : Optimisé pour les calculs de reconnaissance faciale
- **Timeout** : 30 secondes pour les requêtes

### Sécurité

- **HTTPS** : Automatique sur Render
- **CORS** : Configuré pour les domaines autorisés
- **Variables d'environnement** : Sécurisées dans Render

## Monitoring

### Logs en Temps Réel

```bash
# Dans le dashboard Render
# Logs > View Logs
# Vous verrez les logs de démarrage et d'exécution
```

### Métriques

- **Uptime** : Surveillé par Render
- **Performance** : Métriques disponibles dans le dashboard
- **Erreurs** : Logs d'erreur automatiques

## Migration depuis Docker Compose

Si vous aviez un `docker-compose.yml`, il n'est plus nécessaire :

```bash
# Ancien (Docker Compose)
docker-compose up --build

# Nouveau (Render)
# Déploiement automatique via Git
```

## Support

En cas de problème sur Render :

1. **Vérifier les logs** : Dashboard Render > Logs
2. **Tester localement** : `python test_imports.py`
3. **Vérifier les variables** : Dashboard Render > Environment
4. **Rebuild** : Dashboard Render > Manual Deploy

## Avantages Render

✅ **Déploiement automatique** via Git
✅ **HTTPS automatique**
✅ **Monitoring intégré**
✅ **Variables d'environnement sécurisées**
✅ **Logs en temps réel**
✅ **Scalabilité facile** 