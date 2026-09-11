"""
직원 PIN(4자리 숫자) 해시/검증 (스펙 9).

이메일/전화번호 인증 수단이 없는 MVP라 "이름 + 4자리 PIN"으로 로그인한다.
PIN 은 평문으로 저장하지 않고, 매번 다른 salt 를 붙여 PBKDF2 로 해시한다.
"""

import hashlib
import hmac
import secrets

_ITERATIONS = 100_000


def is_valid_pin_format(pin: str) -> bool:
    return len(pin) == 4 and pin.isdigit()


def hash_pin(pin: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), _ITERATIONS).hex()
    return f"{salt}${digest}"


def verify_pin(pin: str, stored: str) -> bool:
    salt, _, _ = stored.partition("$")
    if not salt:
        return False
    return hmac.compare_digest(hash_pin(pin, salt), stored)


def random_pin() -> str:
    """관리자가 PIN을 초기화할 때 쓰는 임시 4자리 PIN."""
    return f"{secrets.randbelow(10000):04d}"
