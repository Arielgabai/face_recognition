# 🔐 Gestion des Mots de Passe avec Comptes Multiples

## 🎯 Question

"Comment gérer des mots de passe différents pour le même email sur des événements différents ?"

---

## ✅ Réponse

**Chaque compte est INDÉPENDANT** avec son propre mot de passe haché.

### Structure en Base de Données

```sql
Table users:
┌────┬──────────────┬─────────────────┬──────────────────┬──────────┐
│ id │ username     │ email           │ hashed_password  │ event_id │
├────┼──────────────┼─────────────────┼──────────────────┼──────────┤
│ 10 │ alice_smith  │ alice@email.com │ $2b$12$Xdf...AB │    1     │ ← Compte 1
│ 20 │ alice_martin │ alice@email.com │ $2b$12$Ygh...CD │    2     │ ← Compte 2
└────┴──────────────┴─────────────────┴──────────────────┴──────────┘
```

**Points clés** :
- ✅ Même email : `alice@email.com`
- ✅ Usernames différents : `alice_smith` vs `alice_martin`
- ✅ **Mots de passe DIFFÉRENTS** : `$2b$12$Xdf...AB` vs `$2b$12$Ygh...CD`
- ✅ Événements différents : `event_id=1` vs `event_id=2`

---

## 🔐 Scénarios de Connexion

### Scénario 1 : Mots de Passe Différents

```
Alice crée :
- Compte événement A : password = "MotDePasse123!"
- Compte événement B : password = "AutrePassword456!"

Login avec alice@email.com :
1. Système trouve 2 comptes
2. Teste le password entré contre les 2 comptes
3. Garde seulement ceux qui matchent
```

**Exemple A** : Alice entre `MotDePasse123!`
```python
valid_users = [u for u in users if verify_password("MotDePasse123!", u.hashed_password)]
# Résultat : [compte événement A]  (1 seul match)
→ Connexion DIRECTE au compte A ✓
```

**Exemple B** : Alice entre `AutrePassword456!`
```python
valid_users = [u for u in users if verify_password("AutrePassword456!", u.hashed_password)]
# Résultat : [compte événement B]  (1 seul match)
→ Connexion DIRECTE au compte B ✓
```

**Exemple C** : Alice entre un mauvais mot de passe
```python
valid_users = [u for u in users if verify_password("WrongPassword!", u.hashed_password)]
# Résultat : []  (aucun match)
→ Erreur 401 "Identifiant ou mot de passe incorrect" ✗
```

---

### Scénario 2 : Même Mot de Passe (Rare mais Possible)

```
Alice crée :
- Compte événement A : password = "MêmePassword123!"
- Compte événement B : password = "MêmePassword123!"  (même mdp)

Login avec alice@email.com + "MêmePassword123!" :
1. Système trouve 2 comptes
2. Teste le password contre les 2
3. Les 2 matchent !
```

**Résultat** : 🔀 **Page de SÉLECTION affichée**
- Événement A (alice_smith)
- Événement B (alice_martin)

→ Alice choisit l'événement

---

## 🎯 Avantages de Ce Système

### 1. Sécurité ✅
Chaque compte a son propre hash indépendant.
- Si un mot de passe est compromis → 1 seul compte affecté
- Les autres comptes restent sécurisés

### 2. Flexibilité ✅
L'utilisateur peut choisir :
- Même mdp pour tous ses événements (pratique)
- Mdps différents par événement (plus sécurisé)

### 3. UX Intelligente ✅
- **Mdps différents** → Login automatique au bon compte (1 seul match)
- **Même mdp** → Sélection événement
- **Username** → Toujours direct (1 compte)

---

## 🔍 Code de Vérification

```python
# Dans /api/login, ligne 2418
valid_users = [u for u in users if verify_password(user_credentials.password, u.hashed_password)]

# verify_password() utilise bcrypt pour comparer :
# - Le mot de passe en clair saisi
# - Le hash stocké en BDD pour chaque compte

# Résultat :
# - Si 1 match → Login direct
# - Si 2+ match → Sélection
# - Si 0 match → Erreur 401
```

---

## 💡 Recommandations Utilisateur

### Lors de l'Inscription

**Message conseillé** :
```
💡 Conseil de Sécurité :
   - Vous pouvez utiliser le même mot de passe pour tous vos événements
   - Ou utiliser des mots de passe différents (plus sécurisé)
   - Conseil : utilisez un gestionnaire de mots de passe !
```

---

### Lors du Login

**Si plusieurs comptes avec même email** :

**Option 1** : Utiliser des mots de passe différents
```
→ Connexion automatique au bon compte (1 seul match)
```

**Option 2** : Utiliser le username
```
→ Connexion directe sans sélection
```

**Option 3** : Utiliser l'email + même mdp
```
→ Sélection événement affichée
```

---

## 🎯 En Résumé

| Situation | Comportement |
|-----------|--------------|
| **Email + mdp différents** | Login direct au compte qui match ✅ |
| **Email + même mdp pour 2+ comptes** | Sélection événement 🔀 |
| **Username + n'importe quel mdp** | Login direct ✅ |
| **Mauvais mdp** | Erreur 401 ❌ |

**C'est un système intelligent qui s'adapte !** 🎉

---

*Guide créé le : 2025-01-05*

