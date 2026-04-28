import secrets

import bcrypt
from sqlmodel import Session, select

from app.models import RecoveryCode

_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_recovery_codes(n: int = 12) -> list[str]:
    def _segment() -> str:
        return "".join(secrets.choice(_ALPHABET) for _ in range(4))

    return [f"{_segment()}-{_segment()}-{_segment()}" for _ in range(n)]


def hash_code(code: str) -> str:
    return bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()


def verify_code(code: str, code_hash: str) -> bool:
    return bcrypt.checkpw(code.encode(), code_hash.encode())


def create_codes_for_user(user_id: int, session: Session) -> list[str]:
    existing = session.exec(select(RecoveryCode).where(RecoveryCode.user_id == user_id)).all()
    for row in existing:
        session.delete(row)
    session.flush()

    plaintext_codes = generate_recovery_codes(12)
    for code in plaintext_codes:
        session.add(RecoveryCode(user_id=user_id, code_hash=hash_code(code)))
    session.commit()
    return plaintext_codes


def consume_code(user_id: int, code: str, session: Session) -> bool:
    rows = session.exec(
        select(RecoveryCode).where(
            RecoveryCode.user_id == user_id,
            RecoveryCode.used == False,  # noqa: E712
        )
    ).all()
    matched_row = None
    for row in rows:
        if verify_code(code, row.code_hash):
            matched_row = row
    if matched_row is not None:
        matched_row.used = True
        session.add(matched_row)
        session.commit()
        return True
    return False
