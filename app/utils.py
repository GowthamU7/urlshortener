import random
import string
import re

BASE62_CHARACTERS = string.ascii_letters + string.digits


def generate_short_code(length: int = 6) -> str:
    return ''.join(random.choices(BASE62_CHARACTERS, k=length))


def is_valid_alias(alias: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_-]+", alias))