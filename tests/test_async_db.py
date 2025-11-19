import os
import asyncio
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from sqlalchemy import text
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

def _to_asyncpg_url(url: str) -> str:
    """Convert a PostgreSQL SQLAlchemy URL to asyncpg, preserving SSL and removing incompatible params."""
    parsed = urlparse(url)
    # Switch scheme to async dialect
    scheme = 'postgresql+asyncpg'
    # Preserve query params except those known to be libpq-specific/incompatible
    q = dict(parse_qsl(parsed.query))
    # Remove channel_binding which asyncpg doesn't use
    q.pop('channel_binding', None)
    # Remove sslmode from URL; we'll pass SSL via connect_args instead
    q.pop('sslmode', None)
    # Build query back
    query = urlencode(q)
    return urlunparse((scheme, parsed.netloc, parsed.path, '', query, ''))

async def async_main() -> None:
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("DATABASE_URL is not set. Skipping async test.")
        return
    db_url_async = _to_asyncpg_url(db_url)

    # Create async engine and test a simple query
    # For managed Postgres (e.g., Supabase/Neon), enforce TLS via connect_args for asyncpg
    connect_args = {"ssl": True}
    engine = create_async_engine(db_url_async, echo=True, connect_args=connect_args)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("select 'hello world'"))
            rows = result.fetchall()
            print(rows)
            assert rows and rows[0][0] == 'hello world'
    finally:
        await engine.dispose()

if __name__ == '__main__':
    asyncio.run(async_main())
    