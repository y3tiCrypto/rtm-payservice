from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

# Construct storage URI if Redis is enabled
if settings.redis_enabled:
    if settings.redis_password:
        storage_uri = f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}"
    else:
        storage_uri = f"redis://{settings.redis_host}:{settings.redis_port}"
    limiter = Limiter(key_func=get_remote_address, storage_uri=storage_uri)
else:
    limiter = Limiter(key_func=get_remote_address)
