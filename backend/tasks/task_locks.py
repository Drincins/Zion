from __future__ import annotations

from contextlib import contextmanager
import logging

import sqlalchemy as sa
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@contextmanager
def try_task_lock(db: Session, lock_key: int):
    """
    Acquire a PostgreSQL advisory lock for the current task run.

    The lock is session-scoped and held on the same DB connection for the
    lifetime of the surrounding Session. This lets us keep the current
    multi-worker deployment while preventing duplicate background job runs.
    """
    acquired = False
    try:
        acquired = bool(
            db.execute(
                sa.text("SELECT pg_try_advisory_lock(:lock_key)"),
                {"lock_key": int(lock_key)},
            ).scalar()
        )
        yield acquired
    finally:
        if acquired:
            try:
                db.execute(
                    sa.text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": int(lock_key)},
                )
            except Exception:
                logger.exception("Failed to release advisory task lock %s", lock_key)
