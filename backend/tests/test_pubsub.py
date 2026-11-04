"""Tests for the in-memory pub/sub bus."""

from __future__ import annotations

import asyncio

import pytest

from app.utils.pubsub import (
    InMemoryPubSub,
    get_pubsub,
    job_channel,
    publish_safe,
    set_pubsub,
)


@pytest.mark.asyncio
async def test_publish_with_no_subscribers_is_noop():
    bus = InMemoryPubSub()
    # Should not raise / hang.
    await bus.publish(job_channel("nope"), {"x": 1})


@pytest.mark.asyncio
async def test_subscriber_receives_published_event():
    bus = InMemoryPubSub()
    channel = job_channel("job-1")

    async with bus.subscribe(channel) as queue:
        await bus.publish(channel, {"hello": "world"})
        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert event == {"hello": "world"}


@pytest.mark.asyncio
async def test_publish_fans_out_to_all_subscribers():
    bus = InMemoryPubSub()
    channel = job_channel("job-1")

    async with bus.subscribe(channel) as q1, bus.subscribe(channel) as q2:
        await bus.publish(channel, {"n": 1})
        e1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        e2 = await asyncio.wait_for(q2.get(), timeout=1.0)
        assert e1 == {"n": 1}
        assert e2 == {"n": 1}


@pytest.mark.asyncio
async def test_subscribers_isolated_by_channel():
    bus = InMemoryPubSub()
    async with bus.subscribe(job_channel("a")) as qa, bus.subscribe(
        job_channel("b")
    ) as qb:
        await bus.publish(job_channel("a"), {"to": "a"})
        assert (await asyncio.wait_for(qa.get(), 1.0)) == {"to": "a"}
        assert qb.empty()


@pytest.mark.asyncio
async def test_unsubscribe_cleans_up_channel():
    bus = InMemoryPubSub()
    channel = job_channel("job-1")
    async with bus.subscribe(channel):
        assert channel in bus._channels
    # Last subscriber gone -> channel entry removed.
    assert channel not in bus._channels


@pytest.mark.asyncio
async def test_full_queue_drops_event_without_blocking_publisher(monkeypatch):
    # Force a tiny queue so we can fill it deterministically.
    monkeypatch.setattr("app.utils.pubsub._QUEUE_MAXSIZE", 2)
    bus = InMemoryPubSub()
    channel = job_channel("job-1")

    async with bus.subscribe(channel) as queue:
        await bus.publish(channel, {"i": 0})
        await bus.publish(channel, {"i": 1})
        # Third publish must not raise/block, just drop.
        await asyncio.wait_for(bus.publish(channel, {"i": 2}), timeout=0.5)
        assert queue.qsize() == 2


@pytest.mark.asyncio
async def test_get_pubsub_returns_singleton():
    set_pubsub(None)  # reset
    a = get_pubsub()
    b = get_pubsub()
    assert a is b
    set_pubsub(None)


@pytest.mark.asyncio
async def test_publish_safe_swallows_publisher_exceptions():
    class _Boom:
        async def publish(self, channel, event):
            raise RuntimeError("boom")

        def subscribe(self, channel):  # pragma: no cover - unused
            raise NotImplementedError

    set_pubsub(_Boom())
    try:
        # Must not raise.
        await publish_safe(job_channel("x"), {"k": "v"})
    finally:
        set_pubsub(None)
