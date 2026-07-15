"""ARQ Redis pool accessor — a thin, mockable seam so router handlers never
construct the pool inline (untestable) and never import arq's create_pool
directly."""
import os

from arq import create_pool
from arq.connections import RedisSettings


async def get_arq_pool():
    return await create_pool(RedisSettings.from_dsn(os.environ.get("REDIS_URL", "redis://localhost:6379")))
