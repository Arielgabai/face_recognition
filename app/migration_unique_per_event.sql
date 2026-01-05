-- ============================================================================
-- MIGRATION : Permettre le même email/username pour des événements différents
-- ============================================================================
-- Cette migration permet à un utilisateur de créer un compte par événement
-- avec le même email, tout en gardant l'unicité email/username par événement
-- ============================================================================

BEGIN;

-- Étape 1: Ajouter la colonne event_id à la table users (nullable)
-- Pour les utilisateurs existants et les photographes/admins, ce sera NULL
ALTER TABLE users ADD COLUMN event_id INTEGER;

-- Étape 2: Ajouter la contrainte foreign key vers events
ALTER TABLE users 
ADD CONSTRAINT users_event_id_fkey 
FOREIGN KEY (event_id) 
REFERENCES events(id) 
ON DELETE SET NULL;

-- Étape 3: Pour les utilisateurs existants, remplir event_id depuis UserEvent
-- (prendre le premier événement auquel ils sont inscrits)
UPDATE users 
SET event_id = (
    SELECT event_id 
    FROM user_events 
    WHERE user_events.user_id = users.id 
    LIMIT 1
)
WHERE user_type = 'user' AND event_id IS NULL;

-- Étape 4: Supprimer les anciennes contraintes unique sur email et username
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key;
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_username_key;

-- Étape 5: Créer des contraintes unique composites (email + event_id) et (username + event_id)
-- Ces contraintes permettent le même email/username pour des événements différents
-- NULL est traité de manière spéciale : deux NULL ne sont pas considérés comme égaux
-- Donc les photographes/admins (event_id=NULL) restent uniques globalement
CREATE UNIQUE INDEX users_email_event_unique 
ON users (email, COALESCE(event_id, -1));

CREATE UNIQUE INDEX users_username_event_unique 
ON users (username, COALESCE(event_id, -1));

-- Note: COALESCE(event_id, -1) permet de traiter les NULL comme -1
-- pour garantir l'unicité des photographes/admins (qui ont event_id=NULL)

-- Étape 6: Créer un index pour améliorer les performances des requêtes
CREATE INDEX idx_users_event_id ON users(event_id);

COMMIT;

-- ============================================================================
-- VÉRIFICATIONS POST-MIGRATION
-- ============================================================================

-- Vérifier que les contraintes sont bien créées
SELECT 
    tablename, 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE tablename = 'users' 
AND (indexname LIKE '%unique%' OR indexname LIKE '%event%');

-- Vérifier qu'il n'y a pas de conflits dans les données existantes
SELECT email, event_id, COUNT(*) 
FROM users 
GROUP BY email, event_id 
HAVING COUNT(*) > 1;

SELECT username, event_id, COUNT(*) 
FROM users 
GROUP BY username, event_id 
HAVING COUNT(*) > 1;

-- ============================================================================
-- ROLLBACK (si nécessaire)
-- ============================================================================
/*
BEGIN;

-- Supprimer les nouveaux index
DROP INDEX IF EXISTS users_email_event_unique;
DROP INDEX IF EXISTS users_username_event_unique;
DROP INDEX IF EXISTS idx_users_event_id;

-- Recréer les anciennes contraintes unique globales
ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email);
ALTER TABLE users ADD CONSTRAINT users_username_key UNIQUE (username);

-- Supprimer la contrainte foreign key
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_event_id_fkey;

-- Supprimer la colonne event_id
ALTER TABLE users DROP COLUMN IF EXISTS event_id;

COMMIT;
*/

