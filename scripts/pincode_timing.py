"""Look up pincodes sequentially vs asyncio.gather. Learning script, not imported by the app."""

from __future__ import annotations

import argparse
import asyncio
import time

import httpx

PINS = [
    "110001",
    "110002",
    "400001",
    "560001",
    "600001",
    "700001",
    "500001",
    "380001",
    "411001",
    "201301",
]
BASE = "https://api.postalpincode.in"


async def lookup(client: httpx.AsyncClient, pin: str, *, block: bool) -> str:
    if block:
        # Deliberate bug: sync sleep freezes the whole event loop.
        time.sleep(2)
    response = await client.get(f"{BASE}/pincode/{pin}", timeout=10.0)
    payload = response.json()
    status = payload[0].get("Status") if payload else "?"
    return f"{pin} {response.status_code} {status}"


async def run(block: bool) -> None:
    async with httpx.AsyncClient() as client:
        started = time.perf_counter()
        sequential = [await lookup(client, pin, block=False) for pin in PINS]
        seq_s = time.perf_counter() - started
        print("sequential (s):", round(seq_s, 3))
        for line in sequential:
            print(" ", line)

        started = time.perf_counter()
        gathered = await asyncio.gather(*[lookup(client, pin, block=block) for pin in PINS])
        gather_s = time.perf_counter() - started
        print("gather (s):", round(gather_s, 3), "block_sleep=", block)
        for line in gathered:
            print(" ", line)

        if block:
            print(
                "Why gather slowed down: time.sleep(2) runs in one coroutine but "
                "blocks the thread, so the event loop cannot progress the other "
                "lookups until the sleep finishes. await asyncio.sleep(2) would "
                "only delay that one task."
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--break",
        dest="block",
        action="store_true",
        help="Put time.sleep(2) inside one async lookup during gather",
    )
    args = parser.parse_args()
    asyncio.run(run(block=args.block))


if __name__ == "__main__":
    main()
