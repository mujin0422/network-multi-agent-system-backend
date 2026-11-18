#!/usr/bin/env python3
"""Run the durable AI workflow worker."""

import asyncio

from app.core.logging import configure_logging
from app.domains.workflow_job.worker import run_workflow_worker


if __name__ == "__main__":
    configure_logging()
    asyncio.run(run_workflow_worker())
