-- ============================================================================
-- DIAGNOSTIC : Pourquoi l'email est-il bloqué ?
-- ============================================================================
-- Exécuter ces requêtes pour identifier le problème
-- ============================================================================

-- Test 1: Vérifier qu'il n'y a PAS les anciennes contraintes unique globales
-- ============================================================================
SELECT 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE tablename = 'users' 
AND indexname IN ('ix_users_email', 'ix_users_username');

-- ATTENDU : 0 ligne (si anciennes contraintes supprimées)
-- SI DES LIGNES APPARAISSENT : C'EST LE PROBLÈME !

-- ============================================================================
-- Test 2: Vérifier les contraintes unique actuelles
-- ============================================================================
SELECT 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE tablename = 'users' 
AND indexname LIKE '%unique%';

-- ATTENDU : Seulement users_email_event_unique et users_username_event_unique

-- ============================================================================
-- Test 3: Vérifier s'il y a des utilisateurs avec cet email
-- ============================================================================
-- REMPLACER 'email@test.com' par l'email problématique
SELECT 
    id, 
    username, 
    email, 
    user_type, 
    event_id, 
    is_active,
    created_at
FROM users 
WHERE email = 'email@test.com';  -- ← REMPLACER ICI

-- Si plusieurs lignes avec event_id différents → C'est OK, c'est voulu
-- Si une ligne avec is_active=false → Utilisateur désactivé, pas supprimé
-- Si aucune ligne → Email libre, le problème est ailleurs

-- ============================================================================
-- Test 4: Vérifier les contraintes au niveau base de données
-- ============================================================================
SELECT 
    conname AS constraint_name,
    contype AS constraint_type,
    pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'users'::regclass
AND contype = 'u';  -- Contraintes UNIQUE

-- ATTENDU : PAS de contrainte unique sur email ou username seuls

-- ============================================================================
-- Test 5: Tester une insertion manuelle (simulation)
-- ============================================================================
-- Essayer d'insérer le même email pour 2 événements différents
BEGIN;

-- Insertion 1 : email@test.com pour event_id=1
INSERT INTO users (username, email, hashed_password, user_type, event_id)
VALUES ('test_user_event1', 'duplicate_test@example.com', 'hash123', 'user', 1);

-- Insertion 2 : MÊME email pour event_id=2
INSERT INTO users (username, email, hashed_password, user_type, event_id)
VALUES ('test_user_event2', 'duplicate_test@example.com', 'hash456', 'user', 2);

-- Si ces deux INSERT réussissent → La BDD est bien configurée ✓
-- Si erreur "duplicate key" → Problème dans les contraintes ✗

-- Annuler les tests
ROLLBACK;

-- ============================================================================
-- SOLUTION : Si les anciennes contraintes sont encore présentes
-- ============================================================================
/*
-- Supprimer les anciennes contraintes unique globales
DROP INDEX IF EXISTS ix_users_email;
DROP INDEX IF EXISTS ix_users_username;

-- Vérifier que c'est bien supprimé
SELECT indexname FROM pg_indexes 
WHERE tablename = 'users' 
AND indexname IN ('ix_users_email', 'ix_users_username');
-- ATTENDU : 0 ligne
*/

