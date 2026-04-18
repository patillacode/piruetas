from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

SESSION_COOKIE = "piruetas_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def sign_session(data: str, secret_key: str) -> str:
    signer = TimestampSigner(secret_key)
    return signer.sign(data).decode()


def unsign_session(token: str, secret_key: str, max_age: int = SESSION_MAX_AGE) -> str | None:
    signer = TimestampSigner(secret_key)
    try:
        return signer.unsign(token, max_age=max_age).decode()
    except (BadSignature, SignatureExpired):
        return None


def make_session_token(user_id: int, is_admin: bool, secret_key: str) -> str:
    data = f"{user_id}:{int(is_admin)}"
    return sign_session(data, secret_key)


def parse_session_token(token: str, secret_key: str) -> tuple[int, bool] | None:
    data = unsign_session(token, secret_key)
    if data is None:
        return None
    try:
        user_id_str, is_admin_str = data.split(":", 1)
        return int(user_id_str), bool(int(is_admin_str))
    except (ValueError, AttributeError):
        return None
