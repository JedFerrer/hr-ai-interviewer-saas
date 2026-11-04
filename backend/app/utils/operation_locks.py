"""Single-worker serialization; not a distributed/exactly-once delivery guarantee."""

import asyncio
import inspect
from functools import wraps
from weakref import WeakValueDictionary

_locks: WeakValueDictionary[tuple, asyncio.Lock] = WeakValueDictionary()


def serialized(namespace: str, argument: str, *, reject_busy: bool = False):
    def decorate(function):
        signature = inspect.signature(function)

        @wraps(function)
        async def wrapped(*args, **kwargs):
            key = (
                asyncio.get_running_loop(),
                namespace,
                signature.bind(*args, **kwargs).arguments[argument],
            )
            lock = _locks.setdefault(key, asyncio.Lock())
            # No await between this check and acquisition: atomic on our single
            # event loop. Queuing an answer could apply it to a later question.
            if reject_busy and lock.locked():
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=409,
                    detail="An interview request is in progress. Reload saved state before retrying.",
                )
            async with lock:
                return await function(*args, **kwargs)

        return wrapped

    return decorate
