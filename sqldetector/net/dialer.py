from __future__ import annotations

"""Happy Eyeballs v2 dialer used by custom transports."""

import asyncio
import socket
from typing import Tuple


async def _open(host: str, port: int, family: int):
    return await asyncio.open_connection(host, port, family=family)


async def create_socket(host: str, port: int) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Race IPv6/IPv4 connection attempts and return the first winner."""

    loop = asyncio.get_event_loop()
    infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    v6 = [info for info in infos if info[0] == socket.AF_INET6]
    v4 = [info for info in infos if info[0] == socket.AF_INET]

    tasks = []
    if v6:
        host6 = v6[0][4][0]
        tasks.append(asyncio.create_task(_open(host6, port, socket.AF_INET6)))
    if v4:
        host4 = v4[0][4][0]
        tasks.append(asyncio.create_task(_open(host4, port, socket.AF_INET)))
    if len(tasks) == 2:
        await asyncio.sleep(0.25)  # stagger
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for t in pending:
        t.cancel()
    return list(done)[0].result()
