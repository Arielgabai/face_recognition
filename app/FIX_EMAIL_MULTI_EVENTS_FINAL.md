# 🎯 Fix Final : Emails Multi-Événements + Sélection d'Événement

## 🐛 Problèmes Identifiés et Résolus

### Problème 1 : `/api/check-user-availability` Bloquait Tout ✅ RÉSOLU

**Symptôme** : Impossible de créer un compte avec un email déjà utilisé (même pour un autre événement)

**Cause** : L'endpoint vérifiait l'unicité **globalement** au lieu de par événement

**Solution** :
```python
# AVANT
result["email_taken"] = db.query(User).filter(User.email == email).first() is not None

# APRÈS
result["email_taken"] = db.query(User).filter(
    (User.email == email) & (User.event_id == event.id)
).first() is not None
```

---

### Problème 2 : Login Ambigu avec Comptes Multiples ✅ RÉSOLU

**Symptôme** : Quand un email a plusieurs comptes (événements différents), on ne sait pas lequel utiliser

**Solution** : Système de sélection d'événement

---

## 📋 Changements Appliqués

### 1. **`/api/check-user-availability`** (main.py) ✅

Maintenant accepte `event_code` et vérifie **uniquement pour cet événement**.

```python
@app.post("/api/check-user-availability")
async def check_user_availability(
    username: str = Body(None),
    email: str = Body(None),
    event_code: str = Body(None),  # ← NOUVEAU
    db: Session = Depends(get_db)
):
    # Vérifier uniquement pour l'événement spécifié
    if username:
        result["username_taken"] = db.query(User).filter(
            (User.username == username) & (User.event_id == event.id)
        ).first() is not None
```

---

### 2. **`/api/login`** (main.py) ✅

Gère maintenant les comptes multiples :

**Comportements** :
- **1 compte** → Login normal, token retourné
- **2+ comptes** → Liste des événements retournée pour sélection

**Nouvelle réponse quand multiples comptes** :
```json
{
  "multiple_accounts": true,
  "accounts": [
    {
      "user_id": 123,
      "username": "alice_event1",
      "event_id": 1,
      "event_name": "Mariage Smith",
      "event_code": "SMITH2024"
    },
    {
      "user_id": 456,
      "username": "alice_event2",
      "event_id": 2,
      "event_name": "Mariage Martin",
      "event_code": "MARTIN2024"
    }
  ],
  "message": "Plusieurs comptes trouvés. Veuillez choisir votre événement."
}
```

**Appel avec user_id pour login spécifique** :
```json
POST /api/login
{
  "username": "alice@email.com",
  "password": "password",
  "user_id": 123  ← Optionnel : pour sélectionner un compte spécifique
}
```

---

### 3. **Page de Sélection** (event_selector.html) ✅

Nouvelle page **`/select-event`** :
- Interface élégante avec cartes cliquables
- Affiche tous les événements de l'utilisateur
- Permet de choisir et se connecter au bon compte

---

### 4. **JavaScript Helper** (login_multi_accounts.js) ✅

Script réutilisable pour intégrer dans index.html, photographer.html, admin.html.

---

## 🚀 Déploiement

### Fichiers Modifiés
- ✅ `main.py` - endpoints check-user-availability + login
- ✅ `static/event_selector.html` - page de sélection (NOUVEAU)
- ✅ `static/login_multi_accounts.js` - helper JavaScript (NOUVEAU)

### Commandes

```bash
cd face_recognition/app

# Build v89
docker build -t findme-prod:v89 .

# Tag & Push
docker tag findme-prod:v89 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v89
aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin 801541932532.dkr.ecr.eu-west-3.amazonaws.com
docker push 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v89

# Update service (modifier update-image.json → v89)
cd ../..
aws apprunner update-service --cli-input-json file://face_recognition/app/update-image.json --region eu-west-3
```

---

## 🎯 Comportement Après Déploiement

### Scénario 1 : Utilisateur avec UN Seul Compte

1. User entre email + password
2. Login normal, token généré
3. Redirection directe vers /gallery

**Comportement** : Inchangé ✓

---

### Scénario 2 : Utilisateur avec PLUSIEURS Comptes (Événements Différents)

1. User entre email@example.com + password
2. Backend détecte 2 comptes (événement A et événement B)
3. **Redirection vers `/select-event`**
4. Page affiche :
   ```
   🎉 Sélection d'Événement
   
   [📋 Mariage Smith - SMITH2024]
   [📋 Mariage Martin - MARTIN2024]
   
   [Continuer vers cet événement]
   ```
5. User clique sur un événement
6. Connexion au compte spécifique
7. Redirection vers /gallery avec les photos de CET événement

**Comportement** : Nouveau, fluide ✓

---

### Scénario 3 : Inscription avec Email Existant (Autre Événement)

1. Alice a déjà un compte alice@email.com pour l'événement A
2. Alice s'inscrit avec alice@email.com pour l'événement B
3. **`/api/check-user-availability`** vérifie uniquement l'événement B
4. ✅ Email disponible pour événement B
5. Compte créé avec succès

**Comportement** : Fonctionne maintenant ✓

---

## 🧪 Tests de Validation

### Test 1 : Inscription Multi-Événements

```
1. Créer compte alice@test.com pour événement MARIAGE_A
2. Créer compte alice@test.com pour événement MARIAGE_B
✓ Les deux comptes devraient être créés
```

### Test 2 : Login avec 1 Compte

```
1. Login avec bob@test.com (1 seul événement)
✓ Connexion directe, pas de sélection
```

### Test 3 : Login avec 2+ Comptes

```
1. Login avec alice@test.com (2 événements)
✓ Redirection vers /select-event
✓ Affichage des 2 événements
✓ Sélection fonctionne
✓ Connexion au bon compte
```

### Test 4 : Suppression et Réutilisation

```
1. Supprimer compte avec email@test.com
2. Recréer avec email@test.com
✓ Fonctionne (email libéré)
```

---

## 📝 Intégration Frontend (Optionnel)

Pour intégrer le support multi-comptes dans les pages existantes (index.html, etc.) :

### Option A : Utiliser le Helper JavaScript

Ajouter `<script src="/static/login_multi_accounts.js"></script>` et utiliser `loginWithMultiAccountSupport()`.

### Option B : Le Backend Gère Tout (Actuel)

Le backend redirige automatiquement vers `/select-event` via la réponse API.
Le frontend doit juste gérer la réponse `multiple_accounts`.

**Exemple de code frontend** :

```javascript
async function login(e) {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    const response = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
    });

    const data = await response.json();

    if (response.ok) {
        if (data.access_token) {
            // Login normal
            localStorage.setItem('token', data.access_token);
            window.location.href = '/gallery';
        } else if (data.multiple_accounts) {
            // Redirection vers sélection
            sessionStorage.setItem('login_accounts', JSON.stringify({
                accounts: data.accounts,
                credentials: { username, password }
            }));
            window.location.href = '/select-event';
        }
    } else {
        showAlert(data.detail || 'Erreur', 'error');
    }
}
```

---

## 🔧 Points d'Attention

### Token JWT

Le token contient maintenant `user_id` en plus de `username` :

```python
create_access_token(
    data={"sub": user.username, "user_id": user.id}
)
```

Cela permet de différencier les comptes même avec le même email.

### SessionStorage vs LocalStorage

- **sessionStorage** : Temporaire (comptes/credentials pour sélection)
- **localStorage** : Persistant (token après login)

---

## 📊 Récapitulatif

| Endpoint | Avant | Après |
|----------|-------|-------|
| `/api/check-user-availability` | Vérif globale ❌ | Vérif par événement ✅ |
| `/api/login` | 1 compte only | Multi-comptes support ✅ |
| `/select-event` | N'existe pas | Page de sélection ✅ |

---

## ✅ Checklist de Déploiement

- [ ] `main.py` modifié (check-user-availability + login)
- [ ] `event_selector.html` créé
- [ ] `login_multi_accounts.js` créé
- [ ] `update-image.json` → v89
- [ ] Image v89 buildée
- [ ] Image v89 pushée vers ECR
- [ ] Service AWS mis à jour
- [ ] Tests effectués (4 scénarios ci-dessus)
- [ ] Documentation partagée

---

*Fix appliqué le : 2025-01-05*
*Version : v89*
*Fonctionnalité : Email Multi-Événements Complète* ✅

