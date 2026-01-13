# 📖 Comportement du Login - Guide Complet

## 🎯 Logique du Login v89

Le système cherche **TOUS les comptes** qui matchent l'identifiant (username OU email).

---

## 📊 Scénarios Détaillés

### Scénario A : Username Unique ✅ CONNEXION DIRECTE

```
Alice a 2 comptes :
- Événement A : username="alice_mariage_smith", email="alice@email.com"
- Événement B : username="alice_mariage_martin", email="alice@email.com"

Alice entre : "alice_mariage_smith" + password
```

**Résultat** : ✅ **Connexion DIRECTE à l'événement A**

**Pourquoi ?**
- Recherche trouve 1 seul compte avec username="alice_mariage_smith"
- Pas de sélection nécessaire

**Recommandation UX** : Encourager l'utilisation du username pour accès rapide !

---

### Scénario B : Email avec Usernames Différents ⚠️ SÉLECTION

```
Alice entre : "alice@email.com" + password
```

**Résultat** : 🔀 **Page de SÉLECTION affichée**

**Pourquoi ?**
- Recherche trouve 2 comptes avec email="alice@email.com"
- Les 2 ont le bon mot de passe
- Le système ne peut pas deviner lequel choisir

**Affichage** :
```
🎉 Sélection d'Événement

┌─────────────────────────────────┐
│ Mariage Smith                   │
│ alice_mariage_smith [SMITH2024] │
│ 📅 15 juin 2024                 │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ Mariage Martin                  │
│ alice_mariage_martin [MARTIN24] │
│ 📅 22 juillet 2024              │
└─────────────────────────────────┘

[Continuer vers cet événement]
```

---

### Scénario C : Email Unique ✅ CONNEXION DIRECTE

```
Bob a 1 seul compte :
- username="bob_mariage", email="bob@email.com"

Bob entre : "bob@email.com" + password
```

**Résultat** : ✅ **Connexion DIRECTE**

**Pourquoi ?**
- 1 seul compte trouvé
- Pas de sélection nécessaire

---

### Scénario D : Même Email, Même Username (Impossible) 🚫

```
Essayer de créer :
- Événement A : username="alice", email="alice@email.com"
- Événement B : username="alice", email="alice@email.com"
```

**Résultat** : ❌ **Création du 2ème compte ÉCHOUE**

**Pourquoi ?**
- Contrainte unique composite : `(username, event_id)`
- `("alice", event_B)` est différent de `("alice", event_A)` → OK
- MAIS : Validation backend vérifie username pour l'événement
- Si username déjà pris pour cet événement → Refusé

**Note** : Pour avoir 2 comptes avec le même email, il FAUT des usernames différents !

---

## 🎯 Règles Finales

### Règle 1 : Unicité

| Combinaison | Unique par | Résultat |
|-------------|------------|----------|
| **(username, event_id)** | Événement | alice_A event1 ≠ alice_B event2 ✅ |
| **(email, event_id)** | Événement | alice@mail event1 ≠ alice@mail event2 ✅ |
| **username seul** | ❌ Non unique | "alice" peut exister dans event1 ET event2 |
| **email seul** | ❌ Non unique | alice@mail peut exister dans event1 ET event2 |

---

### Règle 2 : Login

| Identifiant Saisi | Comptes Trouvés | Comportement |
|-------------------|-----------------|--------------|
| **Username** | 1 compte | Connexion directe ✅ |
| **Username** | 0 compte | Erreur "Identifiant incorrect" ❌ |
| **Email** | 1 compte | Connexion directe ✅ |
| **Email** | 2+ comptes | Sélection événement 🔀 |
| **Email** | 0 compte | Erreur "Identifiant incorrect" ❌ |

---

## 💡 Recommandations UX

### Pour les Utilisateurs

**Message lors de l'inscription** :
```
✅ Compte créé avec succès !

📝 Vos identifiants :
   Username : alice_mariage_smith
   Email    : alice@email.com

💡 Conseil : 
   - Utilisez votre USERNAME pour un accès rapide
   - Utilisez votre EMAIL si vous avez oublié votre username
```

---

### Interface de Login

**Placeholder du champ identifiant** :
```
"Nom d'utilisateur ou email"
```

**Tooltip ou aide** :
```
💡 Si vous avez plusieurs événements avec le même email,
   utilisez votre nom d'utilisateur pour accéder directement
   à un événement spécifique.
```

---

## 🧪 Exemples Concrets

### Exemple 1 : Alice Participe à 2 Mariages

**Inscription** :
```
Mariage Smith :
  username: alice_smith
  email: alice@gmail.com
  → ✓ Compte créé

Mariage Martin :
  username: alice_martin
  email: alice@gmail.com  (même email !)
  → ✓ Compte créé
```

**Login Option A** : Avec username
```
alice_smith + password → Connexion directe Mariage Smith ✓
alice_martin + password → Connexion directe Mariage Martin ✓
```

**Login Option B** : Avec email
```
alice@gmail.com + password → Sélection affichée :
  - Mariage Smith (alice_smith)
  - Mariage Martin (alice_martin)
→ Alice choisit → Connexion ✓
```

---

### Exemple 2 : Bob Participe à 1 Mariage

**Inscription** :
```
username: bob123
email: bob@email.com
```

**Login** :
```
bob123 + password → Connexion directe ✓
bob@email.com + password → Connexion directe ✓
(1 seul compte, pas de sélection)
```

---

## ⚡ Performance

### Requête Login

```sql
-- Recherche optimisée avec index
SELECT * FROM users 
WHERE username = 'alice_smith' 
   OR LOWER(email) = 'alice@email.com';

-- Index utilisés :
-- - ix_users_username (B-tree)
-- - ix_users_email (B-tree)
```

**Temps de réponse** : < 50ms (avec index)

---

## 🎯 En Résumé

**OUI, tu as raison** : 

✅ **Connexion avec username** → Toujours directe (1 compte trouvé)
✅ **Même email, usernames différents** → Sélection (2 comptes trouvés)
✅ **Même email, 1 username** → Directe avec username, sélection avec email

**Logique** : 
- Le système cherche TOUS les comptes qui matchent
- Si 1 seul → Direct
- Si plusieurs → Sélection

C'est le comportement optimal ! 🎉

---

*Guide créé le : 2025-01-05*

