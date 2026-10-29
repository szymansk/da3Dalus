"""In-flight deduplication of ``DedupedCache`` (ARCHITECTURE ch. 8.4, #1332)."""

import asyncio

import pytest
from aero_kernel.cache import DedupedCache, MemoryCache
from aero_kernel.tests.cache_builders import entry

KEY = "sha256:" + "cd" * 32


@pytest.mark.asyncio
async def test_a_released_entry_is_served_to_the_next_claim() -> None:
    cache = DedupedCache(MemoryCache(max_entries=4))
    lease = await cache.claim(KEY)
    assert lease.entry is None
    lease.release(entry(2.0))
    served = (await cache.claim(KEY)).entry
    assert served is not None
    assert served.outputs == {"v": 2.0}


@pytest.mark.asyncio
async def test_a_waiter_gets_the_entry_of_the_run_it_waited_for() -> None:
    cache = DedupedCache(MemoryCache(max_entries=4))
    lease = await cache.claim(KEY)
    waiter = asyncio.create_task(cache.claim(KEY))
    await asyncio.sleep(0)
    lease.release(entry(3.0))
    served = (await waiter).entry
    assert served is not None
    assert served.outputs == {"v": 3.0}


@pytest.mark.asyncio
async def test_a_waiter_of_an_unstored_run_runs_it_and_stores_its_own() -> None:
    cache = DedupedCache(MemoryCache(max_entries=4))
    lease = await cache.claim(KEY)
    waiter = asyncio.create_task(cache.claim(KEY))
    await asyncio.sleep(0)
    lease.release(None)
    own = await waiter
    assert own.entry is None
    own.release(entry(4.0))
    served = (await cache.claim(KEY)).entry
    assert served is not None
    assert served.outputs == {"v": 4.0}


@pytest.mark.asyncio
async def test_a_cancelled_waiter_does_not_cancel_the_run() -> None:
    cache = DedupedCache(MemoryCache(max_entries=4))
    lease = await cache.claim(KEY)
    waiter = asyncio.create_task(cache.claim(KEY))
    await asyncio.sleep(0)
    waiter.cancel()
    await asyncio.gather(waiter, return_exceptions=True)
    lease.release(entry(5.0))
    served = (await cache.claim(KEY)).entry
    assert served is not None
    assert served.outputs == {"v": 5.0}


@pytest.mark.asyncio
async def test_a_lease_is_released_once() -> None:
    cache = DedupedCache(MemoryCache(max_entries=4))
    lease = await cache.claim(KEY)
    lease.release(None)
    lease.release(entry(6.0))  # ignored: the claim is already handed back
    assert (await cache.claim(KEY)).entry is None


def test_a_claim_from_a_second_event_loop_while_a_run_is_in_flight_is_refused() -> None:
    cache = DedupedCache(MemoryCache(max_entries=4))
    asyncio.run(cache.claim(KEY))  # claimed on a first loop and never released
    second_claim = cache.claim(KEY)
    with pytest.raises(RuntimeError, match="one event loop"):
        asyncio.run(second_claim)
