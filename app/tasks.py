import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlmodel import Session, select

from app.database import get_engine
from app.models import Entry, Image, User

logger = logging.getLogger(__name__)


@dataclass
class TaskState:
    name: str
    description: str
    last_run: datetime | None = None
    last_result: str | None = None


_registry: dict[str, TaskState] = {
    "cleanup_images": TaskState(
        name="Orphaned image cleanup",
        description="Deletes uploaded images not linked to any journal entry.",
    ),
    "vacuum_db": TaskState(
        name="Database VACUUM",
        description="Reclaims unused disk space in the SQLite database.",
    ),
    "recalculate_storage": TaskState(
        name="Recalculate storage",
        description="Recalculates disk usage per user from their uploads directory.",
    ),
}


def get_tasks() -> dict[str, TaskState]:
    return _registry


def _record(key: str, result: str) -> None:
    _registry[key].last_run = datetime.now(UTC)
    _registry[key].last_result = result


def run_cleanup_images(data_dir: str) -> str:
    uploads_dir = Path(data_dir) / "uploads"
    with Session(get_engine()) as session:
        all_images = session.exec(select(Image)).all()
        db_filenames = {(img.user_id, img.filename) for img in all_images}
        orphaned: list[Image] = []
        for img in all_images:
            if img.entry_id is None:
                orphaned.append(img)
            elif not session.get(Entry, img.entry_id):
                orphaned.append(img)

        deleted_files = 0
        for img in orphaned:
            path = uploads_dir / str(img.user_id) / img.filename
            try:
                if path.exists():
                    path.unlink()
                    deleted_files += 1
            except Exception:
                logger.exception("Failed to delete file %s", path)
            session.delete(img)

        disk_only = 0
        if uploads_dir.exists():
            for f in uploads_dir.rglob("*"):
                if f.is_file() and (int(f.parent.name), f.name) not in db_filenames:
                    try:
                        f.unlink()
                        disk_only += 1
                    except Exception:
                        logger.exception("Failed to delete untracked file %s", f)

        session.commit()

    result = (
        f"Removed {len(orphaned)} DB records, {deleted_files} linked files, "
        f"{disk_only} untracked files."
    )
    logger.info("cleanup_images: %s", result)
    _record("cleanup_images", result)
    return result


def run_vacuum_db() -> str:
    with get_engine().connect() as conn:
        conn.exec_driver_sql("VACUUM")
    result = "VACUUM completed."
    logger.info("vacuum_db: %s", result)
    _record("vacuum_db", result)
    return result


def _dir_size(directory: Path) -> int:
    total = 0
    for f in directory.rglob("*"):
        if f.is_file():
            try:
                total += f.stat().st_size
            except OSError:
                logger.exception("Failed to stat file %s", f)
    return total


def run_recalculate_storage(data_dir: str) -> str:
    uploads_dir = Path(data_dir) / "uploads"
    with Session(get_engine()) as session:
        users = session.exec(select(User)).all()
        for user in users:
            user_dir = uploads_dir / str(user.id)
            user.storage_bytes = _dir_size(user_dir) if user_dir.exists() else 0
        session.commit()
    result = f"Updated storage for {len(users)} users."
    logger.info("recalculate_storage: %s", result)
    _record("recalculate_storage", result)
    return result


def scheduled_cleanup_images(data_dir: str) -> None:
    run_cleanup_images(data_dir)


def scheduled_vacuum_db() -> None:
    run_vacuum_db()


def scheduled_recalculate_storage(data_dir: str) -> None:
    run_recalculate_storage(data_dir)
