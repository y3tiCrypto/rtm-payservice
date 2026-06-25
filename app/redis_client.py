import redis
import logging
from app.config import settings

logger = logging.getLogger(__name__)

redis_client = None

if settings.redis_enabled:
    try:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=0,
            decode_responses=True
        )
        redis_client.ping()
        logger.info("Redis: Connected successfully.")
    except Exception as e:
        logger.error(f"Redis: Connection failed: {e}. Falling back to local in-memory systems.")
        redis_client = None
