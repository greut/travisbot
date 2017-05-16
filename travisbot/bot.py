"""Discord bot."""

import asyncio
import json
import zlib

from aiohttp import ClientSession, WSMsgType

from . import api


DISPATCH = 0
HEARTBEAT = 1
IDENTIFY = 2
HELLO = 10
HEARTBEAT_ACK = 11


last_sequence = None
"""Global variable holding the sequence number of messages."""
token = None
"""Global variable holding the token... (very ugly)."""  # XXX


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


async def consume(ws, get, fut):
    """Consume the queue and post messages in Discord."""
    while not fut.done():
        data = await get()
        msg = f"{data['repository']['name']}: {data['status_message']}!"
        # XXX this is quite hard coded.
        print(msg)
        asyncio.ensure_future(send_message(309734242085109760, msg))


async def send_message(channel, content):
    """Send a message into the given channel."""
    return await api(f"/channels/{channel}/messages", "POST",
                     token=token,
                     json={"content": content})


async def bot(url, _token, get):
    """Start the bot."""
    global last_sequence, token

    token = _token

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
                    asyncio.ensure_future(consume(ws, get, running))

                elif data["op"] == HEARTBEAT_ACK:
                    pass

                elif data["op"] == DISPATCH:
                    print(data['t'], data['d'])
                    last_sequence = data['s']

                else:
                    print(data)
            # Close the heartbeat
            running.cancel()
