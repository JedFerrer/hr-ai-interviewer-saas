"""Single-worker serialization; not a distributed/exactly-once delivery guarantee."""

import asyncio
import inspect
from functools import wraps
from weakref import WeakValueDictionary

_locks: WeakValueDictionary[tuple, asyncio.Lock] = WeakValueDictionary()


def serialized(namespace: str, argument: str):
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
            async with lock:
                return await function(*args, **kwargs)

        return wrapped

    return decorate
