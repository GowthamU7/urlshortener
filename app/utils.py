import re
from fastapi import HTTPException

BASE62_CHARACTERS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def encode_base62(num: int) -> str:
    if num == 0:
        return BASE62_CHARACTERS[0]

    result = []
    base = len(BASE62_CHARACTERS)

    while num > 0:
        num, remainder = divmod(num, base)
        result.append(BASE62_CHARACTERS[remainder])

    return ''.join(reversed(result))


def is_valid_alias(alias: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_-]+", alias))

def check_rate_limit(redis_client, key: str, limit: int, window_seconds: int = 60):
    current = redis_client.get(key)

    if current is None:
        redis_client.setex(key, window_seconds, 1)
        return

    current_count = int(current)

    if current_count >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {limit} requests per {window_seconds} seconds."
        )

    redis_client.incr(key)