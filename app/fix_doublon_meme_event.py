"""
Script pour identifier et nettoyer les doublons (même email + même event_id)

ATTENTION : Ce script supprime les comptes en double !
Faire un backup avant d'exécuter.

Usage:
    python fix_doublon_meme_event.py --dry-run  (voir sans supprimer)
    python fix_doublon_meme_event.py --fix      (supprimer les doublons)
"""

import os
import sys
import argparse
from sqlalchemy import create_engine, text
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def find_duplicates(engine):
    """Identifier les doublons (même email + même event_id)"""
    print("=" * 70)
    print("🔍 RECHERCHE DE DOUBLONS")
    print("=" * 70)
    print()
    
    with engine.connect() as conn:
        # Trouver les doublons par email + event_id
        result = conn.execute(text("""
            SELECT 
                email, 
                event_id,
                COUNT(*) as count,
                ARRAY_AGG(id ORDER BY created_at) as user_ids,
                ARRAY_AGG(username ORDER BY created_at) as usernames,
                ARRAY_AGG(created_at ORDER BY created_at) as created_dates
            FROM users 
            WHERE event_id IS NOT NULL
            GROUP BY email, event_id 
            HAVING COUNT(*) > 1
        """))
        
        duplicates = result.fetchall()
        
        if not duplicates:
            print("✅ Aucun doublon détecté (email + event_id)")
            print()
            return []
        
        print(f"❌ {len(duplicates)} doublon(s) détecté(s) :")
        print()
        
        dup_list = []
        for dup in duplicates:
            email, event_id, count, user_ids, usernames, created_dates = dup
            
            print(f"Email : {email}")
            print(f"Event ID : {event_id}")
            print(f"Nombre de comptes : {count}")
            print(f"User IDs : {user_ids}")
            print(f"Usernames : {usernames}")
            print(f"Dates création : {[str(d)[:19] for d in created_dates]}")
            print()
            
            dup_list.append({
                'email': email,
                'event_id': event_id,
                'user_ids': user_ids,
                'usernames': usernames,
                'created_dates': created_dates
            })
        
        return dup_list

def fix_duplicates(engine, duplicates, dry_run=True):
    """Supprimer les doublons (garder le plus ancien)"""
    if not duplicates:
        return
    
    print("=" * 70)
    print(f"🔧 {'SIMULATION' if dry_run else 'NETTOYAGE'} DES DOUBLONS")
    print("=" * 70)
    print()
    
    if dry_run:
        print("MODE DRY-RUN : Aucune suppression ne sera effectuée")
        print()
    
    with engine.connect() as conn:
        for dup in duplicates:
            user_ids = dup['user_ids']
            usernames = dup['usernames']
            
            # Garder le premier (plus ancien), supprimer les autres
            keep_id = user_ids[0]
            delete_ids = user_ids[1:]
            
            print(f"Email : {dup['email']}, Event : {dup['event_id']}")
            print(f"  ✓ GARDER : ID {keep_id} (username: {usernames[0]})")
            print(f"  ✗ SUPPRIMER : IDs {delete_ids} (usernames: {usernames[1:]})")
            
            if not dry_run:
                # Supprimer les doublons
                for del_id in delete_ids:
                    # Supprimer les dépendances d'abord
                    conn.execute(text("DELETE FROM user_events WHERE user_id = :uid"), {"uid": del_id})
                    conn.execute(text("DELETE FROM face_matches WHERE user_id = :uid"), {"uid": del_id})
                    conn.execute(text("DELETE FROM password_reset_tokens WHERE user_id = :uid"), {"uid": del_id})
                    conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": del_id})
                    conn.commit()
                    print(f"    → Supprimé ID {del_id}")
            
            print()
    
    if dry_run:
        print("⚠️  MODE DRY-RUN : Aucune modification effectuée")
        print("   Exécuter avec --fix pour supprimer réellement")
    else:
        print("✅ Nettoyage terminé")
    print()

def main():
    parser = argparse.ArgumentParser(description="Identifier et nettoyer les doublons")
    parser.add_argument('--dry-run', action='store_true', help="Voir sans supprimer")
    parser.add_argument('--fix', action='store_true', help="Supprimer réellement les doublons")
    args = parser.parse_args()
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL non défini")
        print("   set DATABASE_URL=postgresql://...")
        sys.exit(1)
    
    print()
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║       NETTOYAGE DES DOUBLONS (même email + même event)        ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()
    
    if not args.dry_run and not args.fix:
        print("⚠️  Veuillez spécifier --dry-run ou --fix")
        print()
        print("Usage :")
        print("  python fix_doublon_meme_event.py --dry-run  (voir sans supprimer)")
        print("  python fix_doublon_meme_event.py --fix      (supprimer)")
        print()
        sys.exit(1)
    
    engine = create_engine(DATABASE_URL)
    
    # Trouver les doublons
    duplicates = find_duplicates(engine)
    
    if not duplicates:
        print("✅ Rien à faire")
        sys.exit(0)
    
    # Nettoyer
    fix_duplicates(engine, duplicates, dry_run=args.dry_run)
    
    if args.dry_run:
        print("Pour nettoyer réellement, exécuter avec --fix")

if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
        load_dotenv("../../.env.local")
    except:
        pass
    
    main()

