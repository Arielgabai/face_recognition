# 🚀 Optimisation Performance - Action Immédiate

## 📊 Situation actuelle

**Test avec 10 users :**
- ❌ `/api/upload-selfie` : **45.5s** en moyenne (20% échecs)
- ❌ `/api/register-with-event-code` : **11s** en moyenne
- ❌ `/api/login` : **5.5s** en moyenne
- ❌ `/api/check-user-availability` : **3.7s** en moyenne

**Objectif : 30 users simultanés avec <5s par requête et <1% échecs**

---

## ⚡ Plan d'action (30 minutes)

### Étape 1 : Ajouter les index DB (5 min)

```bash
# Ajouter les index manquants
python add_performance_indexes.py
```

**Impact attendu :**
- ✅ `check-user-availability` : 3.7s → 0.3s
- ✅ `upload-selfie` (suppression FaceMatch) : 10s → 1s
- ✅ Toutes les requêtes sur événements : 5-20x plus rapides

---

### Étape 2 : Configurer Gunicorn avec workers (5 min)

```bash
# Installer gunicorn si nécessaire
pip install gunicorn uvicorn[standard]

# Arrêter le serveur actuel (Ctrl+C)

# Lancer avec workers multiples
gunicorn main:app -c gunicorn_config.py
```

**Impact attendu :**
- ✅ **8 workers** au lieu d'1 seul
- ✅ Capacité : ~8000 connexions simultanées
- ✅ Tolérance aux requêtes bloquantes

---

### Étape 3 : Vérifier la configuration (2 min)

```bash
# Tester que le serveur répond
curl http://localhost:8000/api/health-check

# Vérifier les stats
curl http://localhost:8000/api/db-raw-test
```

Si erreur, vérifier les variables d'environnement :

```bash
# Optionnel : configurer le pool DB
export DB_POOL_SIZE=30
export DB_MAX_OVERFLOW=70

# Relancer
gunicorn main:app -c gunicorn_config.py
```

---

### Étape 4 : Test de charge progressif (18 min)

```bash
# Rendre le script exécutable
chmod +x test_performance_progressive.sh

# Lancer les tests progressifs
./test_performance_progressive.sh
```

**Tests effectués :**
1. ⚡ 5 users (1 min) - baseline
2. ⚡ 10 users (2 min) - charge modérée
3. ⚡ 20 users (3 min) - charge élevée
4. 🎯 **30 users (5 min) - objectif**

**Résultats attendus après étapes 1-3 :**
```
/api/check-event-code         : 1.5s → 0.1s
/api/check-user-availability   : 3.7s → 0.3s
/api/login                     : 5.5s → 0.5s
/api/register-with-event-code  : 11s  → 2s
/api/upload-selfie            : 45s  → 8s    (encore à optimiser)
Échecs                        : 20%  → 5%
```

---

## 🔧 Optimisations supplémentaires (si nécessaire)

### Si upload-selfie est encore > 8s

Le problème vient de :
1. **Validation synchrone** (Azure API + traitement image)
2. **Suppression des FaceMatch** (même avec index)

**Solution : Rendre l'upload complètement asynchrone**

Voir le document détaillé : `OPTIMISATIONS_PERFORMANCE_LOAD_TEST.md` section "Solution 3"

---

## 📈 Monitoring en temps réel

### Pendant les tests Locust

```bash
# Terminal 1 : Serveur
gunicorn main:app -c gunicorn_config.py

# Terminal 2 : Monitoring
watch -n 1 'curl -s http://localhost:8000/api/stats | jq'

# Terminal 3 : Logs
tail -f /var/log/gunicorn/*.log  # Si configuré
```

### Voir les workers actifs

```bash
# Processus Gunicorn
ps aux | grep gunicorn

# Connexions DB
# (Si PostgreSQL)
psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname='votre_db';"
```

---

## ✅ Critères de succès

- [ ] **Index créés** : 11 index ajoutés
- [ ] **Workers actifs** : 8 workers Gunicorn
- [ ] **Test 30 users réussi** : <1% échecs
- [ ] **Temps moyen < 5s** : 95% des requêtes
- [ ] **Upload selfie < 10s** : Acceptable pour MVP

---

## 🆘 Dépannage

### Erreur : "Address already in use"

```bash
# Tuer les processus sur le port 8000
lsof -ti:8000 | xargs kill -9

# Relancer
gunicorn main:app -c gunicorn_config.py
```

### Erreur : "too many open files"

```bash
# Augmenter les limites (Linux)
ulimit -n 4096

# Relancer
gunicorn main:app -c gunicorn_config.py
```

### Erreur : "Database locked" (SQLite)

```bash
# SQLite n'est pas fait pour la concurrence
# Solution : Passer à PostgreSQL

# Ou réduire temporairement les workers
gunicorn main:app -c gunicorn_config.py --workers 2
```

### Upload-selfie échoue systématiquement

```bash
# Désactiver temporairement la validation stricte
export SELFIE_VALIDATION_STRICT=false

# Relancer
gunicorn main:app -c gunicorn_config.py
```

---

## 📊 Analyser les résultats

### Après les tests

```bash
# Ouvrir les rapports HTML
open results_30users.html

# Ou analyser les CSV
cat results_30users_stats.csv | column -t -s ','
```

### Métriques clés à regarder

| Métrique                  | Objectif | Critique si |
|---------------------------|----------|-------------|
| Temps moyen               | < 5s     | > 10s       |
| P95 (95e percentile)      | < 10s    | > 30s       |
| P99 (99e percentile)      | < 15s    | > 60s       |
| Taux d'échec              | < 1%     | > 5%        |
| Requêtes/sec              | > 10     | < 2         |

---

## 🎯 Après optimisation

Une fois les objectifs atteints :

1. **Documenter** les résultats
2. **Commiter** les changements
3. **Déployer** en staging
4. **Tester** en production avec vrais users
5. **Monitorer** les métriques en continu

---

## 📚 Ressources

- **Documentation complète** : `OPTIMISATIONS_PERFORMANCE_LOAD_TEST.md`
- **Scripts** :
  - `add_performance_indexes.py` - Ajoute les index
  - `gunicorn_config.py` - Config Gunicorn
  - `test_performance_progressive.sh` - Tests automatisés
  - `patch_performance_quick.py` - Patches rapides (optionnel)

---

## 💬 Support

En cas de problème, vérifier :
1. Les logs de Gunicorn
2. Les logs de l'application
3. L'utilisation CPU/RAM
4. Les connexions DB actives

Bonne optimisation ! 🚀
