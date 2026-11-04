"""In-process pub/sub for Server-Sent Events.

Used to fan out candidate-status changes from the background pipeline (and
from manual HR actions) to every recruiter currently watching the same job.

Design notes
------------
The public surface is the :class:`PubSub` protocol. Today the only
implementation is :class:`InMemoryPubSub`, which is correct for a
single-worker uvicorn deployment.

Multi-worker future
~~~~~~~~~~~~~~~~~~~
When we scale to multiple workers (gunicorn/uvicorn workers, Postgres
backend), swap the singleton in ``app.main.lifespan`` to a Redis-backed
implementation. The SSE endpoint and every publish call site stay
identical — only the registry implementation changes. The ``redis_url``
setting in :mod:`app.config` is the natural hook for the swap.

Backpressure
~~~~~~~~~~~~
Subscriber queues are bounded. A slow client cannot accumulate unbounded
events and blow up server memory: when its queue is full the event is
dropped (with a warning). The publisher never blocks — keeping the
background pipeline fast is the priority.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Protocol

logger = logging.getLogger(__name__)

# Bounded per-subscriber queue. 100 events is generous for a UI that only
# patches a single row at a time; if a client falls this far behind, it is
# almost certainly disconnected and we should not buffer further.
_QUEUE_MAXSIZE = 100


class PubSub(Protocol):
    """Minimal pub/sub interface. Implementations may be in-process or remote."""

    async def publish(self, channel: str, event: dict) -> None: ...

    def subscribe(self, channel: str) -> "AsyncIterator[asyncio.Queue]": ...


class InMemoryPubSub:
    """Single-process pub/sub backed by a dict of subscriber queue sets.

    Safe for concurrent ``publish`` and ``subscribe`` calls within one
    asyncio event loop (no cross-thread / cross-process synchronization).
    """

    def __init__(self) -> None:
        self._channels: dict[str, set[asyncio.Queue]] = {}

    async def publish(self, channel: str, event: dict) -> None:
        """Fan an event out to every subscriber of ``channel``.

        Non-blocking: a slow subscriber whose queue is full has the event
        dropped instead of blocking the publisher.
        """
        subscribers = self._channels.get(channel)
        if not subscribers:
            return
        # Snapshot the set so concurrent unsubscribes during iteration are safe.
        for queue in tuple(subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "pubsub: dropping event on channel=%s (subscriber queue full)",
                    channel,
                )

    @asynccontextmanager
    async def subscribe(self, channel: str) -> AsyncIterator[asyncio.Queue]:
        """Context manager yielding a queue that receives events for ``channel``.

        The queue is automatically removed from the channel on exit, and the
        channel entry itself is cleaned up when its last subscriber leaves.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        self._channels.setdefault(channel, set()).add(queue)
        try:
            yield queue
        finally:
            subscribers = self._channels.get(channel)
            if subscribers is not None:
                subscribers.discard(queue)
                if not subscribers:
                    self._channels.pop(channel, None)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
#
# A singleton keeps call sites trivial — background tasks (which don't have
# easy access to the FastAPI ``app`` instance) and request handlers alike can
# just call ``get_pubsub().publish(...)``. The singleton is created lazily so
# tests can swap it via :func:`set_pubsub` without standing up a real app.

_pubsub: PubSub | None = None


def get_pubsub() -> PubSub:
    """Return the process-wide pub/sub instance, creating it on first use."""
    global _pubsub
    if _pubsub is None:
        _pubsub = InMemoryPubSub()
    return _pubsub


def set_pubsub(pubsub: PubSub | None) -> None:
    """Override the singleton (used by lifespan setup and by tests)."""
    global _pubsub
    _pubsub = pubsub


# ---------------------------------------------------------------------------
# Channel naming + safe-publish helper
# ---------------------------------------------------------------------------


def job_channel(job_id: str) -> str:
    """Channel name for events scoped to a single job's candidate list."""
    return f"job:{job_id}"


async def publish_safe(channel: str, event: dict) -> None:
    """Publish swallowing all errors.

    Pub/sub is best-effort UX sugar; a failure here must never break the
    surrounding business operation (resume scoring, status update, etc.).
    """
    try:
        await get_pubsub().publish(channel, event)
    except Exception:  # pragma: no cover - defensive
        logger.exception("pubsub publish failed (channel=%s)", channel)
