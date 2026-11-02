"""Periodic approval expiry sweep independent of the browser lifecycle."""

import asyncio
import logging
from datetime import UTC, datetime

from app.core.config.settings import Settings
from app.domains.execution.repositories.approval_timeout import ApprovalTimeoutRepository

logger = logging.getLogger(__name__)


async def run_approval_timeout_worker(settings: Settings) -> None:
    """Check immediately on startup, then periodically while FastAPI is running.

    Uses a thread for the synchronous SQLAlchemy repository so HTTP event loops
    remain responsive. The repository is idempotent and safe with many workers.
    """
    repository = ApprovalTimeoutRepository(settings.database_url)
    while True:
        try:
            task_ids = await asyncio.to_thread(
                repository.expire_due_approvals,
                datetime.now(UTC),
                settings.approval_timeout_minutes,
            )
            if task_ids:
                logger.warning(
                    "Approval timeout finalized %d task(s): %s",
                    len(task_ids),
                    ", ".join(task_ids),
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Approval expiry sweep failed; retrying next interval")
        await asyncio.sleep(settings.approval_sweep_interval_seconds)
