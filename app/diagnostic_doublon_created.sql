-- ============================================================================
-- DIAGNOSTIC : Comment un doublon a-t-il pu être créé ?
-- ============================================================================
-- REMPLACER l'email problématique ci-dessous
-- ============================================================================

-- 1. Trouver les doublons (même email + même event_id)
SELECT 
    id,
    username,
    email,
    user_type,
    event_id,
    created_at
FROM users 
WHERE email = 'EMAIL_PROBLÉMATIQUE'  -- ← REMPLACER ICI
ORDER BY event_id, created_at;

-- Si 2+ lignes avec le même event_id → DOUBLON DÉTECTÉ ✗

-- ============================================================================
-- 2. Vérifier que les contraintes existent vraiment
-- ============================================================================
SELECT 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE tablename = 'users' 
AND indexname IN ('users_email_event_unique', 'users_username_event_unique');

-- DOIT retourner 2 lignes

-- ============================================================================
-- 3. Vérifier qu'elles sont bien UNIQUE
-- ============================================================================
SELECT 
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename = 'users' 
AND indexdef LIKE '%UNIQUE%';

-- users_email_event_unique DOIT contenir "UNIQUE"
-- users_username_event_unique DOIT contenir "UNIQUE"

-- ============================================================================
-- 4. Tester la contrainte manuellement
-- ============================================================================
BEGIN;

-- Essayer de créer un doublon volontairement
INSERT INTO users (username, email, hashed_password, user_type, event_id)
VALUES ('test_duplicate', 'test_dup@test.com', 'hash1', 'user', 1);

-- Essayer de créer le doublon
INSERT INTO users (username, email, hashed_password, user_type, event_id)
VALUES ('test_duplicate', 'test_dup@test.com', 'hash2', 'user', 1);
-- ^ Ceci DOIT échouer avec "duplicate key value violates constraint"

ROLLBACK;  -- Annuler les tests

-- ============================================================================
-- 5. SI LES CONTRAINTES N'EXISTENT PAS, LES RECRÉER
-- ============================================================================
/*
-- Supprimer si existe (pour recréer proprement)
DROP INDEX IF EXISTS users_email_event_unique;
DROP INDEX IF EXISTS users_username_event_unique;

-- Recréer avec UNIQUE
CREATE UNIQUE INDEX users_email_event_unique 
ON users (email, COALESCE(event_id, -1));

CREATE UNIQUE INDEX users_username_event_unique 
ON users (username, COALESCE(event_id, -1));

-- Vérifier
\d users
*/

-- ============================================================================
-- 6. NETTOYER LES DOUBLONS EXISTANTS (si nécessaire)
-- ============================================================================
/*
-- Identifier les doublons
WITH duplicates AS (
    SELECT 
        email, 
        event_id, 
        MIN(id) as keep_id,
        ARRAY_AGG(id ORDER BY created_at) as all_ids,
        COUNT(*) as count
    FROM users 
    WHERE event_id IS NOT NULL
    GROUP BY email, event_id 
    HAVING COUNT(*) > 1
)
SELECT * FROM duplicates;

-- Supprimer les doublons (garder le plus ancien)
-- ATTENTION : À adapter selon vos besoins (garder le bon compte)
DELETE FROM users 
WHERE id IN (
    SELECT id FROM users u1
    WHERE EXISTS (
        SELECT 1 FROM users u2
        WHERE u2.email = u1.email 
        AND u2.event_id = u1.event_id
        AND u2.id < u1.id  -- Garder le plus ancien
    )
);
*/

