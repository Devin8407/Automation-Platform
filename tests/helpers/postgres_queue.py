from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from automation_platform.execution_queue.postgres.model import QueueEntryModel

# ==================================================================================================
# Public API
# ==================================================================================================


def create_postgres_queue_entry(
    session: Session,
    *,
    task_execution_id: UUID,
    claimed_by: UUID | None = None,
    claim_token: UUID | None = None,
    queued_at: datetime | None = None,
    claimed_at: datetime | None = None,
    last_heartbeat: datetime | None = None,
) -> None:
    """Insert an unclaimed queue entry into the PostgreSQL queue.

    This helper is intended for integration test setup.
    """

    session.execute(
        insert(QueueEntryModel).values(
            task_execution_id=task_execution_id,
            claimed_by=claimed_by,
            claim_token=claim_token,
            queued_at=queued_at or datetime.now(timezone.utc),
            claimed_at=claimed_at,
            last_heartbeat=last_heartbeat,
        )
    )

    session.commit()


def create_claimed_postgres_queue_entry(
    session: Session,
    *,
    task_execution_id: UUID,
    claimed_by: UUID | None = None,
    claim_token: UUID | None = None,
    queued_at: datetime | None = None,
    claimed_at: datetime | None = None,
    last_heartbeat: datetime | None = None,
) -> None:
    """Insert a claimed queue entry into the PostgreSQL queue.

    Any omitted lease metadata is populated with valid default values,
    allowing tests to easily create active worker leases.
    """

    now = datetime.now(timezone.utc)

    create_postgres_queue_entry(
        session=session,
        task_execution_id=task_execution_id,
        claimed_by=claimed_by or uuid4(),
        claim_token=claim_token or uuid4(),
        queued_at=queued_at or now,
        claimed_at=claimed_at or now,
        last_heartbeat=last_heartbeat or now,
    )
