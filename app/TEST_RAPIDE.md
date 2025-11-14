# Test Rapide des Optimisations

## 🚀 Démarrage

### 1. Redémarrer l'application

```bash
cd face_recognition/app
python main.py
```

### 2. Vérifier les logs de démarrage

Vous devriez voir:
```
[Startup] Photo queue initialized with 0 pending jobs
[FaceRecognition][AWS] Using region: eu-west-1
```

✅ Si vous voyez ces lignes, la queue est active !

## 🧪 Test 1: Upload de photos (2 minutes)

### Objectif
Vérifier que les photos sont mises en queue rapidement.

### Étapes

1. **Démarrer le local watcher** (dans un autre terminal)
   ```bash
   cd face_recognition/app
   python local_watcher.py
   ```

2. **Copier 5-10 photos** dans le dossier surveillé
   ```bash
   cp /chemin/vers/photos/*.jpg /dossier/surveillé/
   ```

3. **Observer les logs**
   
   **Vous devriez voir rapidement:**
   ```
   [upload] -> photo1.jpg ct=image/jpeg
   [upload] <- ok: {"enqueued": 1, ...}
   [PhotoQueue] Job xxx enqueued (queue size: 1)
   ```
   
   **Puis en arrière-plan:**
   ```
   [PhotoWorker-0] Processing job xxx: photo1.jpg
   [PhotoWorker-0] Job xxx completed: photo_12345.jpg
   ```

### ✅ Résultat attendu
- Upload rapide (< 5 secondes pour 10 photos)
- Pas de timeout
- Traitement en arrière-plan visible dans les logs

### ❌ Si ça ne marche pas
- Vérifiez que la queue démarre: `grep "Photo queue initialized" logs`
- Vérifiez les erreurs: `grep "ERROR\|Exception" logs`

## 🧪 Test 2: Cache utilisateur (1 minute)

### Objectif
Vérifier que le cache réduit les requêtes DB.

### Étapes

1. **Se connecter comme utilisateur**
   ```bash
   curl -X POST http://localhost:8000/api/login \
     -H "Content-Type: application/json" \
     -d '{"username": "user1", "password": "password"}'
   ```
   
   Récupérer le token: `{"access_token": "xxx..."}`

2. **Accéder aux photos 3 fois de suite**
   ```bash
   for i in {1..3}; do
     curl -H "Authorization: Bearer xxx" \
       http://localhost:8000/api/my-photos
   done
   ```

3. **Vérifier les stats du cache**
   ```bash
   curl -H "Authorization: Bearer xxx" \
     http://localhost:8000/api/admin/queue/stats | jq '.cache'
   ```

### ✅ Résultat attendu
```json
{
  "user_photos_cache": {
    "size": 1,
    "hits": 2,      // ← 2 hits sur 3 requêtes !
    "misses": 1,
    "hit_rate": "66.67%"
  }
}
```

### ❌ Si ça ne marche pas
- Vérifiez que le cache est importé dans main.py
- Le TTL est peut-être expiré (30s)

## 🧪 Test 3: Accès concurrent (5 minutes)

### Objectif
L'utilisateur peut accéder à son espace pendant un upload massif.

### Étapes

1. **Terminal 1: Démarrer un gros upload (50+ photos)**
   ```bash
   # Copier beaucoup de photos
   cp /chemin/vers/photos/*.jpg /dossier/surveillé/
   ```

2. **Terminal 2: En même temps, accéder à la galerie**
   ```bash
   while true; do
     curl -H "Authorization: Bearer xxx" \
       http://localhost:8000/api/my-photos \
       -w "\nTemps: %{time_total}s\n"
     sleep 2
   done
   ```

### ✅ Résultat attendu
- Temps de réponse < 1s même pendant l'upload
- Pas de timeout
- Pas de plantage

### ❌ Si ça plante
- Réduire `PHOTO_QUEUE_WORKERS` à 2
- Réduire `AWS_CONCURRENT_REQUESTS` à 5

## 🧪 Test 4: Monitoring (30 secondes)

### Objectif
Surveiller la queue en temps réel.

### Commande

```bash
watch -n 2 'curl -s -H "Authorization: Bearer xxx" \
  http://localhost:8000/api/admin/queue/stats | jq'
```

### ✅ Résultat attendu
```json
{
  "queue": {
    "total_enqueued": 50,
    "total_processed": 45,
    "total_failed": 0,
    "current_queue_size": 5,
    "workers_active": 3
  },
  "cache": {
    "user_photos_cache": {
      "hit_rate": "85.00%"
    }
  }
}
```

Vous verrez `total_processed` augmenter en temps réel !

## 🐛 Dépannage rapide

### La queue ne démarre pas
```bash
# Vérifier les imports
grep "from photo_queue import" app/main.py

# Vérifier les logs
tail -f logs | grep "Photo queue"
```

### Les photos ne sont pas traitées
```bash
# Vérifier que les workers tournent
curl -H "Authorization: Bearer xxx" \
  http://localhost:8000/api/admin/queue/stats | jq '.queue.workers_active'

# Doit retourner: 3
```

### Le cache ne fonctionne pas
```bash
# Vérifier les stats
curl -H "Authorization: Bearer xxx" \
  http://localhost:8000/api/admin/queue/stats | jq '.cache'

# Si "hits": 0, le cache n'est pas utilisé
```

## 📊 Benchmark simple

### Mesurer les performances

```bash
# Test sans cache (première requête)
time curl -H "Authorization: Bearer xxx" \
  http://localhost:8000/api/my-photos > /dev/null

# Test avec cache (deuxième requête)
time curl -H "Authorization: Bearer xxx" \
  http://localhost:8000/api/my-photos > /dev/null
```

**Attendu:**
- Sans cache: 1-2s
- Avec cache: < 0.5s

## ✅ Checklist de validation

- [ ] La queue démarre au démarrage
- [ ] Les photos sont uploadées en < 1s
- [ ] Les photos sont traitées en arrière-plan
- [ ] Le cache fonctionne (hit_rate > 60%)
- [ ] Pas de plantage pendant l'upload massif
- [ ] Temps de réponse utilisateur < 1s
- [ ] Les workers sont actifs (workers_active > 0)
- [ ] Pas de timeout dans les logs

## 🎉 Si tous les tests passent

**Félicitations !** Votre application est maintenant optimisée et peut gérer:
- ✅ Des centaines de photos en parallèle
- ✅ Des accès utilisateurs concurrents
- ✅ Sans plantage ni timeout

## 📚 Prochaines étapes

1. Tester en production avec charge réelle
2. Ajuster les paramètres selon les besoins
3. (Optionnel) Appliquer le rate limiting
4. Monitorer les métriques AWS

## 🆘 Support

Si un test échoue:
1. Vérifiez les logs complets
2. Consultez `RÉSUMÉ_OPTIMISATIONS.md`
3. Vérifiez la configuration dans `.env`

---

**Durée totale des tests:** ~10 minutes  
**Pré-requis:** Application démarrée, compte utilisateur créé

