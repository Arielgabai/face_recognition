╔════════════════════════════════════════════════════════════════╗
║                    FIX TIMEOUT APPLIQUÉ ✅                      ║
║                   3 COMMANDES À EXÉCUTER                        ║
╚════════════════════════════════════════════════════════════════╝

🔧 PROBLÈME CORRIGÉ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ligne 5200 de main.py : Matching maintenant dans ThreadPool
→ Plus de timeout sur /api/register-with-event-code


⚡ 1. AJOUTER VARIABLE AWS (CRITIQUE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AWS Console → App Runner → findme-prod-v7 → Configuration

Ajouter :
  MATCHING_THREAD_POOL_SIZE = 10


🚀 2. DÉPLOYER (Windows PowerShell)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cd face_recognition/app
.\deploy_fix_timeout.ps1


🧪 3. TESTER (30 users)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cd face_recognition/app
locust -f locust_file.py --host=https://votre-app.onrender.com

Ouvrir : http://localhost:8089
Lancer : 30 users, spawn 5/s


✅ RÉSULTAT ATTENDU
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
/api/register-with-event-code : < 5s (était 11s)
/api/upload-selfie : < 10s (était 45s avec 20% fail)
Aucun "WORKER TIMEOUT" dans les logs


📖 DOCS COMPLÈTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- ACTION_IMMEDIATE_FIX_TIMEOUT.txt  (guide détaillé)
- FIX_FINAL_REGISTER_TIMEOUT.md     (diagnostic)
- DEPLOY_MAINTENANT_V101.md         (déploiement complet)


═══════════════════════════════════════════════════════════════
Version : v101 | Date : 19/01/2026 | Status : ✅ READY
═══════════════════════════════════════════════════════════════
