# 🔧 Fix : Erreur "exec ./start.sh: no such file or directory"

## 🐛 Problème

```
exec ./start.sh: no such file or directory
```

Cette erreur survient lors du déploiement Docker sur AWS.

## 🎯 Causes Possibles

### 1. **Fins de ligne Windows (CRLF) - CAUSE LA PLUS PROBABLE** ⚠️

Sous Windows, les fichiers texte utilisent `CRLF` (\r\n) comme fin de ligne.
Linux attend `LF` (\n).

**Impact** : Le shell Linux ne reconnaît pas le fichier comme un script valide.

### 2. Fichier non copié dans l'image

Le fichier n'est pas présent dans l'image Docker finale.

### 3. Permissions incorrectes

Le fichier n'a pas les droits d'exécution.

---

## ✅ Solutions Appliquées

### Fix 1 : Conversion des fins de ligne dans Dockerfile ✓

**Modifié** : `Dockerfile` ligne 61

```dockerfile
# AVANT
RUN chmod +x start.sh

# APRÈS
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh
```

Cette commande :
1. `sed -i 's/\r$//'` : Supprime les `\r` (CRLF → LF)
2. `chmod +x` : Rend le fichier exécutable

### Fix 2 : Utiliser bash explicitement ✓

**Modifié** : `Dockerfile` ligne 67

```dockerfile
# AVANT
CMD ["./start.sh"]

# APRÈS
CMD ["/bin/bash", "./start.sh"]
```

Spécifie explicitement bash comme interpréteur.

---

## 🚀 Déploiement

### Étape 1 : Rebuild l'image Docker

```bash
cd face_recognition/app

# Build
docker build -t findme-prod:v8 .
```

### Étape 2 : Test local (optionnel)

```bash
# Tester l'image localement avant de pusher
docker run -p 10000:10000 \
  -e DATABASE_URL="votre_db_url" \
  -e AWS_REGION="eu-west-1" \
  findme-prod:v8
```

Si ça fonctionne localement, continuer au push.

### Étape 3 : Push vers AWS ECR

```bash
# Tag
docker tag findme-prod:v8 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v8

# Login ECR
aws ecr get-login-password --region eu-west-3 | \
  docker login --username AWS --password-stdin \
  801541932532.dkr.ecr.eu-west-3.amazonaws.com

# Push
docker push 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v8
```

### Étape 4 : Update service AWS

```bash
aws apprunner update-service \
  --cli-input-json file://../../service.json \
  --region eu-west-3
```

---

## 🔍 Vérification

### Dans les logs AWS CloudWatch

Après le déploiement, vous devriez voir :

```
🚀 Démarrage de l'application Face Recognition sur Render...
📋 Test des importations Python...
✅ Toutes les importations sont OK
🔧 Application du patch face_recognition_models...
✅ Patch face_recognition_models appliqué avec succès
📁 Création des dossiers nécessaires...
🔍 Vérification de la structure de la base de données...
✅ Structure de la base de données vérifiée
🌐 Démarrage du serveur avec Gunicorn...
  - Workers: 5
  - Port: 10000
  - Timeout: 120s
[INFO] Starting gunicorn 21.2.0
[INFO] Booting worker with pid: ...
```

---

## 🛠️ Alternative : Convertir manuellement sous Windows

Si le problème persiste, convertir le fichier localement avant le build :

### Option A : Git

```bash
# Configurer Git pour gérer automatiquement les fins de ligne
git config core.autocrlf input

# Re-checkout le fichier
git rm --cached start.sh
git add start.sh
git commit -m "Fix line endings for start.sh"
```

### Option B : VS Code

1. Ouvrir `start.sh` dans VS Code
2. En bas à droite, cliquer sur "CRLF"
3. Sélectionner "LF"
4. Sauvegarder le fichier

### Option C : PowerShell (Windows)

```powershell
# Convertir le fichier
(Get-Content start.sh -Raw) -replace "`r`n", "`n" | Set-Content start.sh -NoNewline
```

### Option D : WSL/Git Bash

```bash
dos2unix start.sh
```

---

## 🐛 Troubleshooting

### Erreur persiste après rebuild

**Vérifier** que le fichier est bien dans l'image :

```bash
# Inspecter l'image Docker
docker run --rm -it findme-prod:v8 /bin/bash

# Dans le container
ls -la start.sh
cat start.sh | head -1   # Devrait afficher #!/bin/bash
file start.sh            # Devrait afficher "Bourne-Again shell script, ASCII text executable"
```

### Le fichier n'existe pas dans l'image

**Vérifier** le `.dockerignore` :

```bash
cat .dockerignore
# start.sh NE DOIT PAS être listé
```

Si `start.sh` est dans `.dockerignore`, le retirer.

### Permissions incorrectes

```bash
# Dans le container
ls -la start.sh
# Devrait afficher: -rwxr-xr-x ... start.sh
#                   ^^^ = exécutable
```

Si pas exécutable, problème avec `chmod +x` dans le Dockerfile.

---

## 📋 Checklist de Vérification

Avant de redéployer :

- [ ] Dockerfile modifié avec `sed -i 's/\r$//'` ✓
- [ ] CMD modifié pour utiliser `/bin/bash` ✓
- [ ] Fins de ligne converties en LF (optionnel mais recommandé)
- [ ] `.dockerignore` ne contient pas `start.sh`
- [ ] Image rebuildée avec les changements
- [ ] Test local effectué (optionnel)
- [ ] Image pushée vers ECR
- [ ] Service AWS mis à jour

---

## 🎯 Prévention Future

### Configuration Git (recommandé)

Ajouter à `.gitattributes` (créer le fichier à la racine du repo) :

```gitattributes
# Forcer LF pour les scripts shell
*.sh text eol=lf

# Auto pour les autres fichiers
* text=auto
```

Puis :

```bash
git add .gitattributes
git rm --cached -r .
git reset --hard
git commit -m "Fix line endings configuration"
```

### Configuration VS Code

Ajouter à `.vscode/settings.json` :

```json
{
  "files.eol": "\n",
  "[shellscript]": {
    "files.eol": "\n"
  }
}
```

---

## 📚 Ressources

- [Docker CMD documentation](https://docs.docker.com/engine/reference/builder/#cmd)
- [Line endings in Git](https://docs.github.com/en/get-started/getting-started-with-git/configuring-git-to-handle-line-endings)
- [dos2unix utility](https://waterlan.home.xs4all.nl/dos2unix.html)

---

*Fix appliqué le : 2025-01-05*
*Version : 1.0*

