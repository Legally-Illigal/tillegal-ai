"""Apply pending SQL migrations to the Supabase PostgreSQL database."""

import asyncio
from pathlib import Path

import psycopg
from pydantic import SecretStr

from src.core.config import load_settings

DATABASE_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = DATABASE_DIR / "supabase" / "migrations"
MIGRATION_LOCK_NAME = "tillegal-ai-schema-migrations"


async def run_supabase_migrations(database_url: SecretStr) -> None:
    """Apply each unapplied SQL migration using the configured database connection."""
    await asyncio.to_thread(_run_supabase_migrations, database_url.get_secret_value())


def _run_supabase_migrations(database_url: str) -> None:
    """Run migrations in a worker thread to support Windows event loops."""
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        raise FileNotFoundError(f"No SQL migrations found in {MIGRATIONS_DIR}")

    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute("SELECT pg_advisory_lock(hashtext(%s))", (MIGRATION_LOCK_NAME,))
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS public.schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

            for migration_file in migration_files:
                version = migration_file.name
                cursor = connection.execute(
                    "SELECT EXISTS (SELECT 1 FROM public.schema_migrations WHERE version = %s)",
                    (version,),
                )
                if cursor.fetchone()[0]:
                    continue

                migration_sql = migration_file.read_text(encoding="utf-8")
                with connection.transaction():
                    connection.execute(migration_sql, prepare=False)
                    connection.execute(
                        "INSERT INTO public.schema_migrations (version) VALUES (%s)",
                        (version,),
                    )
        finally:
            connection.execute("SELECT pg_advisory_unlock(hashtext(%s))", (MIGRATION_LOCK_NAME,))


async def main() -> None:
    """Run pending migrations using DATABASE_URL from the application environment."""
    database_url = load_settings().supabase.database_url
    if database_url is None:
        raise ValueError("DATABASE_URL must be set before running database migrations")
    await run_supabase_migrations(database_url)


if __name__ == "__main__":
    asyncio.run(main())
