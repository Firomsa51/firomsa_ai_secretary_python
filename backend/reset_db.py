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

        # 2. Drop existing outdated app tables so FastAPI/SQLAlchemy recreates them
        #    with ALL current columns. CASCADE handles FK dependency order.
        for table in ("messages", "conversations", "users", "settings"):
            await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
        logger.info(
            "Dropped old app tables (messages, conversations, users, settings). "
            "FastAPI will recreate them clean with all columns."
        )

        await conn.close()
    except Exception as err:
        logger.error("Error executing DB fix: %s", err)


if __name__ == "__main__":
    asyncio.run(fix_database_schema())
