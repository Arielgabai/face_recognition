# Face Recognition App - Application de Reconnaissance Faciale

Une application web moderne pour la gestion et la reconnaissance faciale de photos d'événements (mariages, événements, etc.).

## 🚀 Fonctionnalités Principales

### ✅ Problèmes Résolus

1. **Photos qui disparaissent** - Corrigé avec une meilleure gestion des événements
2. **Séparation des événements** - Interface pour changer d'événement pour les photographes
3. **Filtrage par événement** - Les utilisateurs voient uniquement les photos de leur événement
4. **Codes événement manuels** - Option pour entrer le code à la main
5. **Reconnaissance faciale automatique** - Déclenchement lors d'ajout/modification

### 🎯 Nouvelles Fonctionnalités

#### Pour les Utilisateurs
- **Sélecteur d'événements** : Changer facilement entre les événements auxquels ils sont inscrits
- **Rejoindre un événement** : Saisir manuellement un code événement
- **Filtrage intelligent** : Voir uniquement les photos de l'événement sélectionné
- **Inscription avec code** : Créer un compte avec un code événement

#### Pour les Photographes
- **Gestion multi-événements** : Gérer plusieurs événements simultanément
- **Upload par événement** : Uploader des photos pour un événement spécifique
- **Vue organisée** : Voir toutes les photos par événement

#### Pour les Admins
- **Codes événement complexes** : Générer des codes alphanumériques de 8 caractères
- **Codes personnalisés** : Définir des codes événement personnalisés
- **Gestion avancée** : Interface complète de gestion des événements

## 🛠️ Installation et Configuration

### Prérequis
- Python 3.8+
- Node.js 16+
- SQLite (ou PostgreSQL pour la production)

### Installation Backend
```bash
cd app
pip install -r requirements.txt
```

### Installation Frontend
```bash
cd app/frontend
npm install
npm run build
```

### Configuration
1. Copier `.env.example` vers `.env`
2. Configurer les variables d'environnement
3. Lancer la base de données

## 🚀 Démarrage

### Développement
```bash
# Backend
cd app
python main.py

# Frontend (optionnel pour le développement)
cd app/frontend
npm start
```

### Production
```bash
# Utiliser le Dockerfile fourni
docker-compose up -d
```

## 📋 Scripts de Maintenance

### Nettoyage de la Base de Données
```bash
cd app
python cleanup_orphaned_photos.py
```

### Reconnaissance Faciale Automatique
```bash
# Pour un événement spécifique
python auto_face_recognition.py event <event_id>

# Pour un utilisateur spécifique
python auto_face_recognition.py user <user_id>

# Optimisation générale
python auto_face_recognition.py optimize
```

## 🔧 API Endpoints

### Nouveaux Endpoints

#### Gestion des Événements
- `GET /api/photographer/events` - Événements du photographe
- `GET /api/user/events` - Événements de l'utilisateur
- `POST /api/join-event` - Rejoindre un événement
- `POST /api/register-with-event-code` - Inscription avec code

#### Upload par Événement
- `POST /api/photographer/events/{event_id}/upload-photos` - Upload photos pour événement
- `GET /api/photographer/events/{event_id}/photos` - Photos d'un événement
- `GET /api/user/events/{event_id}/photos` - Photos utilisateur par événement

#### Codes Événement
- `POST /api/admin/generate-event-code` - Générer code complexe
- `POST /api/admin/set-event-code` - Définir code personnalisé

## 🎨 Interface Utilisateur

### Composants Ajoutés
- `EventSelector` : Sélection d'événements pour utilisateurs
- `JoinEvent` : Rejoindre un événement avec code
- `PhotographerEventManager` : Gestion des événements pour photographes
- `RegisterWithEventCode` : Inscription avec code événement

### Améliorations UX
- Interface intuitive pour changer d'événement
- Feedback visuel pour les actions
- Gestion des erreurs améliorée
- Chargement progressif des données

## 🔒 Sécurité

### Authentification
- JWT tokens avec expiration
- Vérification des permissions par type d'utilisateur
- Protection des routes sensibles

### Validation
- Vérification des codes événement
- Validation des fichiers uploadés
- Contrôle d'accès aux événements

## 📊 Performance

### Optimisations
- Cache des encodages faciaux
- Traitement par lot des photos
- Requêtes optimisées par événement
- Nettoyage automatique des données orphelines

### Monitoring
- Logs détaillés des opérations
- Métriques de reconnaissance faciale
- Alertes sur les erreurs

## 🐛 Résolution des Problèmes

### Photos qui Disparaissent
- ✅ Association automatique des photos aux événements
- ✅ Nettoyage des photos orphelines
- ✅ Vérification d'intégrité des données

### Gestion des Événements
- ✅ Interface multi-événements pour photographes
- ✅ Filtrage par événement pour utilisateurs
- ✅ Codes événement complexes et personnalisables

### Reconnaissance Faciale
- ✅ Déclenchement automatique lors d'upload
- ✅ Mise à jour lors de modification de selfie
- ✅ Optimisation des performances

## 🔄 Workflow Typique

### Pour un Photographe
1. Se connecter à l'interface photographe
2. Sélectionner l'événement à gérer
3. Uploader des photos pour cet événement
4. Les photos sont automatiquement analysées
5. Les utilisateurs voient leurs photos correspondantes

### Pour un Utilisateur
1. S'inscrire avec un code événement (QR ou manuel)
2. Uploader une selfie
3. Changer d'événement si nécessaire
4. Voir les photos où ils apparaissent

### Pour un Admin
1. Créer des événements et assigner des photographes
2. Générer des codes événement complexes
3. Gérer les utilisateurs et photographes
4. Monitorer les performances

## 📈 Améliorations Futures

- [ ] Interface mobile responsive
- [ ] Notifications push
- [ ] Export des photos
- [ ] Analytics avancées
- [ ] Intégration avec d'autres services

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature
3. Commiter les changements
4. Pousser vers la branche
5. Ouvrir une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails. 