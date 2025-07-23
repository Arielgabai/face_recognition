# Face Recognition Web Application

Une application web moderne de reconnaissance faciale construite avec FastAPI, React et PostgreSQL.

## 🚀 Fonctionnalités

### Pour les Utilisateurs
- **Inscription/Connexion** : Système d'authentification sécurisé
- **Upload de Selfie** : Les utilisateurs peuvent uploader une photo de leur visage
- **Galerie Personnelle** : Visualisation de toutes les photos où ils apparaissent
- **Galerie Générale** : Accès à toutes les photos disponibles

### Pour les Photographes
- **Upload de Photos** : Possibilité d'uploader des photos qui seront analysées
- **Reconnaissance Automatique** : Le système détecte automatiquement les visages des utilisateurs
- **Gestion des Photos** : Interface pour gérer les photos uploadées

## 🛠️ Technologies Utilisées

### Backend
- **FastAPI** : Framework web moderne et rapide
- **SQLAlchemy** : ORM pour la gestion de la base de données
- **PostgreSQL** : Base de données relationnelle
- **face_recognition** : Bibliothèque Python pour la reconnaissance faciale
- **OpenCV** : Traitement d'images
- **JWT** : Authentification sécurisée

### Frontend
- **React** : Framework JavaScript pour l'interface utilisateur
- **TypeScript** : Typage statique pour JavaScript
- **Material-UI** : Composants UI modernes
- **React Router** : Navigation entre les pages
- **Axios** : Client HTTP pour les appels API

### Infrastructure
- **Docker** : Conteneurisation de l'application
- **Docker Compose** : Orchestration des services

## 📋 Prérequis

- Docker et Docker Compose
- Node.js 18+ (pour le développement local)
- Python 3.11+ (pour le développement local)

## 🚀 Installation et Démarrage

### Avec Docker (Recommandé)

1. **Cloner le repository**
   ```bash
   git clone <repository-url>
   cd face_recognition
   ```

2. **Démarrer l'application**
   ```bash
   cd app
   docker-compose up --build
   ```

3. **Accéder à l'application**
   - Frontend : http://localhost:8000
   - API Documentation : http://localhost:8000/docs

### Développement Local

1. **Backend**
   ```bash
   cd app
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

2. **Frontend**
   ```bash
   cd app/frontend
   npm install
   npm start
   ```

## 📁 Structure du Projet

```
face_recognition/
├── app/
│   ├── frontend/                 # Application React
│   │   ├── src/
│   │   │   ├── components/      # Composants React
│   │   │   ├── contexts/        # Contextes React
│   │   │   ├── services/        # Services API
│   │   │   └── types/           # Types TypeScript
│   │   └── public/              # Fichiers statiques
│   ├── static/                  # Fichiers statiques du backend
│   │   └── uploads/             # Photos uploadées
│   ├── main.py                  # Point d'entrée FastAPI
│   ├── models.py                # Modèles de base de données
│   ├── schemas.py               # Schémas Pydantic
│   ├── auth.py                  # Authentification
│   ├── face_recognizer.py       # Logique de reconnaissance faciale
│   ├── database.py              # Configuration base de données
│   ├── requirements.txt         # Dépendances Python
│   ├── Dockerfile               # Configuration Docker
│   └── docker-compose.yml       # Orchestration Docker
└── README.md
```

## 🔧 Configuration

### Variables d'Environnement

- `DATABASE_URL` : URL de connexion à la base de données
- `SECRET_KEY` : Clé secrète pour les tokens JWT

### Base de Données

L'application utilise PostgreSQL avec les tables suivantes :
- `users` : Informations des utilisateurs
- `photos` : Métadonnées des photos
- `face_matches` : Correspondances faciales détectées

## 🔐 Sécurité

- Authentification JWT
- Hachage des mots de passe avec bcrypt
- Validation des fichiers uploadés
- Protection CORS configurée

## 📱 Utilisation

1. **Créer un compte** : Inscrivez-vous en tant qu'utilisateur ou photographe
2. **Upload de selfie** (utilisateurs) : Uploadez une photo de votre visage
3. **Upload de photos** (photographes) : Uploadez des photos à analyser
4. **Visualisation** : Consultez vos photos dans la galerie

## 🐛 Dépannage

### Problèmes Courants

1. **Erreur de reconnaissance faciale**
   - Vérifiez que les images contiennent des visages clairs
   - Assurez-vous que les images sont au format JPG/PNG

2. **Problèmes de base de données**
   - Vérifiez que PostgreSQL est démarré
   - Contrôlez les variables d'environnement

3. **Problèmes Docker**
   - Nettoyez les conteneurs : `docker-compose down -v`
   - Reconstruisez : `docker-compose up --build`

## 🤝 Contribution

1. Fork le projet
2. Créez une branche feature (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 📞 Support

Pour toute question ou problème, veuillez ouvrir une issue sur GitHub. 