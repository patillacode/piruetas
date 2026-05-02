from sqlmodel import Session, select

from app.database import get_engine, init_db
from app.models import User
from app.settings import get_settings

import bcrypt

settings = get_settings()

print(f"DEMO_ENABLED : {settings.demo_enabled}")
print(f"DEMO_USERNAME: {settings.demo_username}")

if not settings.demo_enabled:
    print("Demo is disabled — set DEMO_ENABLED=true and re-run.")
    raise SystemExit(1)

init_db()
with Session(get_engine()) as session:
    user = session.exec(select(User).where(User.username == settings.demo_username)).first()
    if not user:
        print(f"User '{settings.demo_username}' not found — nothing to reset.")
        raise SystemExit(1)
    hashed = bcrypt.hashpw(settings.demo_password.encode(), bcrypt.gensalt()).decode()
    user.hashed_password = hashed
    user.session_version += 1
    session.add(user)
    session.commit()
    print(f"Password reset for '{settings.demo_username}'. All existing sessions invalidated.")
