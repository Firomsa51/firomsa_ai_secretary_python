import asyncio
import os
import asyncpg


async def reset_alembic():
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print("DATABASE_URL not set, skipping DB reset.")
        return

    # Convert asyncpg driver string if needed
    clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(clean_url)
        await conn.execute("DROP TABLE IF EXISTS alembic_version CASCADE;")
        await conn.close()
        print("Successfully dropped alembic_version table.")
    except Exception as e:
        print(f"Error resetting alembic table: {e}")


if __name__ == "__main__":
    asyncio.run(reset_alembic())
