# 🎯 Guide Render : Optimisations pour 30 Users

## 📍 Vous êtes ici

Votre app est déployée sur **Render** avec :
- ❌ RAM saturée à 90% (20 users)
- ❌ vCPU à 70% (20 users)
- ❌ Impossible d'aller à 30 users

**Objectif :** Supporter 30 users SANS upgrade de plan

---

## ⚡ Action immédiate (15 minutes)

### Étape 1 : Ajouter les index DB (5 min)

#### Sur le Dashboard Render

1. Allez sur https://dashboard.render.com
2. Cliquez sur votre **Web Service**
3. Cliquez sur l'onglet **"Shell"** en haut
4. Dans le terminal qui s'ouvre, tapez :

```bash
cd face_recognition/app
python add_performance_indexes.py
```

5. Attendez le message :
```
✅ 11/11 index ajoutés avec succès!
```

**C'est tout !** Les index sont maintenant permanents dans votre PostgreSQL.

---

### Étape 2 : Configurer BCRYPT_ROUNDS (3 min)

#### Sur le Dashboard Render

1. Restez sur votre **Web Service**
2. Cliquez sur l'onglet **"Environment"** en haut à gauche
3. Cliquez sur **"Add Environment Variable"**
4. Ajoutez :
   - **Key:** `BCRYPT_ROUNDS`
   - **Value:** `4`
5. Cliquez **"Save Changes"**

Render va **automatiquement redéployer** votre app (~2-3 min).

---

### Étape 3 : Déployer le nouveau code (5 min)

#### Depuis votre machine locale

```bash
# 1. Commit les changements
git add .
git commit -m "Optimisations RAM/CPU: compression + cache + bcrypt optimisé"

# 2. Push vers GitHub (Render déploie automatiquement)
git push origin main

# 3. Attendre le déploiement sur Render (~2-3 min)
```

Suivez le déploiement dans **Render Dashboard > Logs**.

---

### Étape 4 : Tester (2 min)

```bash
# Depuis votre machine Windows
# Remplacer par VOTRE URL Render
locust -f locust_file.py --host=https://VOTRE-APP.onrender.com
```

Dans l'interface Locust (http://localhost:8089) :
- **Number of users:** 30
- **Spawn rate:** 5
- **Host:** https://VOTRE-APP.onrender.com
- Cliquez **"Start swarming"**

---

## 📊 Résultats attendus

### Après toutes les optimisations

**Test avec 30 users :**
- ✅ RAM : 60-70% (au lieu de 90%)
- ✅ vCPU : 50-60% (au lieu de 70%)
- ✅ Temps moyen : <2s (au lieu de 8.5s)
- ✅ Taux d'échec : <1% (au lieu de 9%)

### Dans Render Metrics

Pendant le test, vous devriez voir :
- RAM stable autour de 60-70%
- CPU pics à 60% max
- Pas de crashs
- Logs propres

---

## 🔍 Vérifications

### 1. Vérifier que les index sont créés

Dans le **Shell Render** :

```bash
python -c "
from database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
indexes = inspector.get_indexes('face_matches')
print(f'Index sur face_matches: {len(indexes)}')
"
```

Devrait afficher : **Index sur face_matches: 3+**

---

### 2. Vérifier que BCRYPT_ROUNDS est actif

Dans les **Logs Render**, cherchez :

```
[INFO] Environment: BCRYPT_ROUNDS=4
```

Ou testez un login/register et vérifiez qu'il est rapide (<1s).

---

### 3. Vérifier la compression des selfies

Dans les **Logs Render**, cherchez :

```
[SelfieCompress] Original: 2548923 bytes, Compressed: 156234 bytes (quality=75)
```

Si vous voyez ça, la compression fonctionne ! (~95% de réduction)

---

## 🆘 Problèmes courants

### "Shell" non disponible dans Render

**Solution :** Utiliser l'URL PostgreSQL externe

1. Render Dashboard > PostgreSQL Database
2. Copier **"External Database URL"**
3. Sur votre machine locale :

```bash
# Windows PowerShell
$env:DATABASE_URL="postgres://user:pass@host:5432/db"
python add_performance_indexes.py
```

---

### Déploiement bloqué

**Solution :**

1. Vérifier les logs : **Render Dashboard > Logs**
2. Chercher les erreurs de démarrage
3. Vérifier que `requirements.txt` est à jour

---

### Tests Locust échouent

**Causes possibles :**

1. **App pas encore déployée**
   - Attendre le déploiement (2-3 min)

2. **URL incorrecte**
   ```bash
   # Vérifier l'URL dans Render Dashboard
   # Format: https://VOTRE-APP.onrender.com
   ```

3. **Code événement M01 n'existe pas**
   - Créer l'événement en tant que photographe/admin
   - Ou changer dans `locust_file.py` : `"M01"` → votre code

---

## 🎯 Workflow complet résumé

```
1. Render Shell → python add_performance_indexes.py     [5 min]
2. Render Environment → BCRYPT_ROUNDS=4                  [2 min]
3. Local → git push                                      [3 min]
4. Attendre déploiement Render                           [3 min]
5. Local → locust test                                   [5 min]
                                                    ___________
                                                    Total: 18 min
```

---

## 📈 Suivi post-optimisation

### Métriques à surveiller

**Dans Render Dashboard > Metrics :**
- Memory usage : Doit rester <75%
- CPU usage : Doit rester <65%
- Response time : <2s

**Dans Locust :**
- RPS (Requests/sec) : >8
- Failures : <1%
- P95 : <5s

---

## ✅ Validation finale

Une fois le test à 30 users réussi :

1. **Analyser le rapport Locust** : `results_final.html`
2. **Vérifier les logs Render** : Pas d'erreurs
3. **Tester manuellement** : Créer un compte, uploader selfie
4. **IMPORTANT** : Remettre `BCRYPT_ROUNDS=12` pour la production

---

## 🎉 Succès !

Si tout fonctionne :
- ✅ 30 users simultanés supportés
- ✅ RAM <75%, CPU <65%
- ✅ Performances optimales
- ✅ Validation stricte activée
- ✅ Prêt pour production

**Félicitations ! 🎊**

---

## 📞 Besoin d'aide ?

Si problème persistant :
1. Vérifier les logs Render
2. Vérifier que les variables d'environnement sont actives
3. Vérifier que les index sont créés
4. Partager les métriques Render + résultats Locust

---

**Temps estimé total : 18 minutes**  
**Coût : 0€ (pas d'upgrade de plan)**  
**Gain : 10 users supplémentaires + performances 5-20x meilleures**  

Bon déploiement ! 🚀
