-- Migration: Add show_in_general column to photos table
-- Description: Allows photographers to manually select which photos appear in "Général" tab
-- Date: 2025-11-25

-- Check if column exists (PostgreSQL)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='photos' AND column_name='show_in_general'
    ) THEN
        -- Add the column
        ALTER TABLE photos 
        ADD COLUMN show_in_general BOOLEAN DEFAULT NULL;
        
        RAISE NOTICE 'Column show_in_general added successfully';
    ELSE
        RAISE NOTICE 'Column show_in_general already exists, skipping';
    END IF;
END $$;

-- Verify the column was added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name='photos' AND column_name='show_in_general';

