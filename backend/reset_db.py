import asyncio
import logging
import os
import asyncpg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reset_db")


async def fix_database_schema() -> None:
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        logger.warning("DATABASE_URL variable is not set. Skipping DB fix.")
        return

    # Clean connection string for raw asyncpg
    clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        conn = await asyncpg.connect(clean_url)
        
        # 1. Reset alembic version table
        await conn.execute("DROP TABLE IF EXISTS alembic_version CASCADE;")
        logger.info("Dropped alembic_version table.")

        # 2. Add missing column 'auto_reply_enabled' directly if it doesn't exist
        await conn.execute("""
            DO $$ 
            BEGIN 
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='settings') THEN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='settings' AND column_name='auto_reply_enabled') THEN
                        ALTER TABLE settings ADD COLUMN auto_reply_enabled BOOLEAN DEFAULT TRUE;
                    END IF;
                END IF;
            END $$;
        """)
        logger.info("Ensured 'auto_reply_enabled' column exists in settings table.")

        await conn.close()
    except Exception as err:
        logger.error("Error executing DB fix: %s", err)


if __name__ == "__main__":
    asyncio.run(fix_database_schema())
