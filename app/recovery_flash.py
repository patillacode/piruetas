import json

from itsdangerous import BadSignature, URLSafeSerializer
from starlette.responses import Response

RECOVERY_FLASH_COOKIE = "piruetas_recovery_flash"
_RECOVERY_FLASH_MAX_AGE = 60 * 10  # 10 minutes


def _signer(secret_key: str) -> URLSafeSerializer:
    return URLSafeSerializer(secret_key, salt="recovery-flash")


def set_recovery_flash(
    response: Response, codes: list[str], secret_key: str, secure: bool
) -> None:
    serializer = _signer(secret_key)
    value = serializer.dumps(codes)
    response.set_cookie(
        RECOVERY_FLASH_COOKIE,
        value,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=_RECOVERY_FLASH_MAX_AGE,
    )


def pop_recovery_flash(request_cookies: dict, secret_key: str) -> list[str] | None:
    raw = request_cookies.get(RECOVERY_FLASH_COOKIE)
    if not raw:
        return None
    try:
        serializer = _signer(secret_key)
        codes = serializer.loads(raw)
        if isinstance(codes, list):
            return codes
        return None
    except BadSignature:
        return None
