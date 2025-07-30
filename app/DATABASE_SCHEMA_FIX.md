# Database Schema Fix Guide

## Problem
The application is failing with the error:
```
psycopg2.errors.UndefinedColumn: column users.selfie_data does not exist
```

This happens because the database schema is missing the `selfie_data` column that is defined in the `User` model.

## Root Cause
The `User` model in `models.py` defines a `selfie_data` column:
```python
selfie_data = Column(LargeBinary, nullable=True)  # Données binaires de la selfie
```

But the actual database table doesn't have this column, causing SQLAlchemy to fail when trying to query it.

## Solution

### Option 1: Run the Fix Script (Recommended)

1. **For Local Development:**
   ```bash
   cd app
   python fix_database_schema.py
   ```

2. **For Render Deployment:**
   Since this is deployed on Render, you need to run the fix script on the deployed instance. You can do this by:

   a. **Using Render's Shell:**
   - Go to your Render dashboard
   - Navigate to your service
   - Click on "Shell" tab
   - Run: `python fix_database_schema.py`

   b. **Or add it to your startup script:**
   - Modify your `start.sh` to include the fix:
   ```bash
   #!/bin/bash
   python fix_database_schema.py
   python main.py
   ```

### Option 2: Manual Database Migration

If you have direct database access, you can run this SQL command:

**For PostgreSQL:**
```sql
ALTER TABLE users ADD COLUMN selfie_data BYTEA;
```

**For SQLite:**
```sql
ALTER TABLE users ADD COLUMN selfie_data BLOB;
```

### Option 3: Recreate Database (Development Only)

If you're in development and can afford to lose data:

1. Delete the database file (if using SQLite)
2. Restart the application - it will recreate all tables with the correct schema

## Verification

After running the fix, you can verify it worked by:

1. **Checking the login endpoint works**
2. **Running this query to verify the column exists:**
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'users' AND column_name = 'selfie_data';
   ```

## Files Created

- `fix_database_schema.py` - Script to automatically fix the schema
- `add_selfie_data_column.py` - Simple script to add just the missing column

## Next Steps

After fixing the schema:

1. **Run the migration script** to populate existing selfie data:
   ```bash
   python migrate_photos_to_db.py
   ```

2. **Test the application** to ensure login works properly

3. **Monitor logs** to ensure no more database errors

## Prevention

To prevent this in the future:

1. **Always run database migrations** when deploying schema changes
2. **Use Alembic** for proper database migrations
3. **Test schema changes** in a staging environment first 