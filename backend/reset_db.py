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

    # Clean connection string for direct asyncpg
    clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        conn = await asyncpg.connect(clean_url)

        # 1. Drop alembic version table
        await conn.execute("DROP TABLE IF EXISTS alembic_version CASCADE;")
        logger.info("Dropped alembic_version table.")

        # 2. Drop existing outdated 'settings' table so FastAPI/SQLAlchemy recreates it with ALL columns
        await conn.execute("DROP TABLE IF EXISTS settings CASCADE;")
        logger.info(
            "Dropped old settings table. FastAPI will recreate it clean with all columns."
        )

        await conn.close()
    except Exception as err:
        logger.error("Error executing DB fix: %s", err)


if __name__ == "__main__":
    asyncio.run(fix_database_schema())
