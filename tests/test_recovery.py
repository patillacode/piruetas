import re

from itsdangerous import URLSafeSerializer
from sqlmodel import select

from app.models import RecoveryCode
from app.recovery import consume_code, create_codes_for_user, generate_recovery_codes
from app.recovery_flash import RECOVERY_FLASH_COOKIE, pop_recovery_flash

_TEST_SECRET = "test-secret-key-not-for-production"


def test_generate_recovery_codes_count_and_format():
    codes = generate_recovery_codes()
    assert len(codes) == 12
    pattern = re.compile(r"^[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}$")
    for code in codes:
        assert pattern.match(code), f"Bad format: {code}"


def test_create_codes_for_user_creates_12(session, regular_user):
    codes = create_codes_for_user(regular_user.id, session)
    assert len(codes) == 12
    rows = session.exec(select(RecoveryCode).where(RecoveryCode.user_id == regular_user.id)).all()
    assert len(rows) == 12
    for row in rows:
        assert not row.used


def test_create_codes_for_user_replaces_old_codes(session, regular_user):
    create_codes_for_user(regular_user.id, session)
    create_codes_for_user(regular_user.id, session)
    rows = session.exec(select(RecoveryCode).where(RecoveryCode.user_id == regular_user.id)).all()
    assert len(rows) == 12


def test_consume_code_valid(session, regular_user):
    codes = create_codes_for_user(regular_user.id, session)
    result = consume_code(regular_user.id, codes[0], session)
    assert result is True
    rows = session.exec(
        select(RecoveryCode).where(
            RecoveryCode.user_id == regular_user.id,
            RecoveryCode.used == True,  # noqa: E712
        )
    ).all()
    assert len(rows) == 1


def test_consume_code_already_used(session, regular_user):
    codes = create_codes_for_user(regular_user.id, session)
    consume_code(regular_user.id, codes[0], session)
    result = consume_code(regular_user.id, codes[0], session)
    assert result is False


def test_consume_code_invalid(session, regular_user):
    create_codes_for_user(regular_user.id, session)
    result = consume_code(regular_user.id, "AAAA-AAAA-AAAA", session)
    assert result is False


def test_consume_code_cross_user_isolation(session, regular_user, admin_user):
    codes = create_codes_for_user(regular_user.id, session)
    result = consume_code(admin_user.id, codes[0], session)
    assert result is False


def test_pop_recovery_flash_non_list_payload():
    s = URLSafeSerializer(_TEST_SECRET, salt="recovery-flash")
    cookies = {RECOVERY_FLASH_COOKIE: s.dumps({"not": "a list"})}
    assert pop_recovery_flash(cookies, _TEST_SECRET) is None


def test_pop_recovery_flash_bad_signature():
    cookies = {RECOVERY_FLASH_COOKIE: "tampered.value"}
    assert pop_recovery_flash(cookies, _TEST_SECRET) is None
