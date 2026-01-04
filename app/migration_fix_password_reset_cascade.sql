-- Migration pour ajouter CASCADE à la contrainte foreign key password_reset_tokens -> users
-- Exécutez ce script sur votre base de données PostgreSQL pour appliquer la modification

-- Étape 1: Supprimer l'ancienne contrainte
ALTER TABLE password_reset_tokens 
DROP CONSTRAINT IF EXISTS password_reset_tokens_user_id_fkey;

-- Étape 2: Recréer la contrainte avec ON DELETE CASCADE
ALTER TABLE password_reset_tokens 
ADD CONSTRAINT password_reset_tokens_user_id_fkey 
FOREIGN KEY (user_id) 
REFERENCES users(id) 
ON DELETE CASCADE;

-- Vérifier que la modification a été appliquée
SELECT 
    tc.table_name, 
    tc.constraint_name, 
    tc.constraint_type,
    rc.delete_rule
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.referential_constraints rc 
    ON tc.constraint_name = rc.constraint_name
WHERE tc.table_name = 'password_reset_tokens'
    AND tc.constraint_type = 'FOREIGN KEY';

