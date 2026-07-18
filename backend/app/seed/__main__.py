"""CLI-раннер сидов: `uv run python -m app.seed`."""

import asyncio

from app.core.db import session_factory
from app.seed.categories import seed_categories
from app.seed.geo import seed_geo


async def main() -> None:
    async with session_factory() as session:
        await seed_geo(session)
        await seed_categories(session)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
