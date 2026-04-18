from app.database import get_engine, init_db, seed_admin
from sqlmodel import Session

init_db()
with Session(get_engine()) as s:
    seed_admin(s)
print("Admin seeded.")
