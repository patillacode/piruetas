import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlmodel import Session, select

from app.database import get_engine
from app.models import Entry, Image

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
}


def get_tasks() -> dict[str, TaskState]:
    return _registry


def _record(key: str, result: str) -> None:
    _registry[key].last_run = datetime.now(UTC)
    _registry[key].last_result = result


def run_cleanup_images(data_dir: str) -> str:
    uploads_dir = Path(data_dir) / "uploads"
    with Session(get_engine()) as session:
        db_filenames = set(session.exec(select(Image.filename)).all())

        all_images = session.exec(select(Image)).all()
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
                if f.is_file() and f.name not in db_filenames:
                    try:
                        f.unlink()
                        disk_only += 1
                    except Exception:
                        logger.exception("Failed to delete untracked file %s", f)

        session.commit()

    result = f"Removed {len(orphaned)} DB records, {deleted_files} linked files, {disk_only} untracked files."
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


def scheduled_cleanup_images(data_dir: str) -> None:
    run_cleanup_images(data_dir)


def scheduled_vacuum_db() -> None:
    run_vacuum_db()
