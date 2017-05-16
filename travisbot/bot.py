"""Discord bot."""

import asyncio
import json
import zlib

from aiohttp import ClientSession, WSMsgType


DISPATCH = 0
HEARTBEAT = 1
IDENTIFY = 2
HELLO = 10
HEARTBEAT_ACK = 11


last_sequence = None
"""Global variable holding the sequence number of messages."""


async def heartbeat(ws, interval, fut):
    """Send beats regularly to keep the ws connected."""
    interval /= 1000  # seconds
    await asyncio.sleep(interval)
    while not fut.done():
        await ws.send_json({
            "op": HEARTBEAT,
            "d": last_sequence
        })
        await asyncio.sleep(interval)


async def consume(ws, queue, fut):
    """Consume the queue and post messages in Discord."""
    while not fut.done():
        data = await queue.get()
        print(f"{data['repository']['name']}: {data['status_message']}!")
        # XXX post the message in the #bots channel.


async def bot(url, token, queue):
    """Start the bot."""
    global last_sequence

    running = asyncio.Future()

    with ClientSession() as session:
        async with session.ws_connect(f"{url}?v=5&encoding=json") as ws:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                elif msg.type == WSMsgType.BINARY:
                    data = json.loads(zlib.decompress(msg.data))
                else:
                    print("unknown type", msg.type)

                if data["op"] == HELLO:
                    await ws.send_json({
                        "op": IDENTIFY,
                        "d": {
                            "token": token,
                            "properties": {},
                            "compress": True,
                            "large_threshold": 250
                        }
                    })

                    # Heartbeat
                    interval = data['d']['heartbeat_interval']
                    asyncio.ensure_future(heartbeat(ws, interval, running))
                    # Consumer
                    asyncio.ensure_future(consume(ws, queue, running))

                elif data["op"] == HEARTBEAT_ACK:
                    pass

                elif data["op"] == DISPATCH:
                    print(data['t'], data['d'])
                    last_sequence = data['s']

                else:
                    print(data)
            # Close the heartbeat
            running.cancel()
