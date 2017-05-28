"""Discord bot."""

import asyncio
import json
import zlib

from aiohttp import ClientSession, WSMsgType

from . import api

API_VERSION = 6

DISPATCH = 0
HEARTBEAT = 1
IDENTIFY = 2
HELLO = 10
HEARTBEAT_ACK = 11


class Bot:
    """The bot."""

    def __init__(self, url, token, get):
        """Init the bot.

        :param url: The Gateway URL (WebSocket)
        :param token: The Discord API token
        :param get: The Queue reader side.
        """
        self.url = url

        self.last_sequence = None
        """The sequence number of messages."""

        self.token = token
        """The authentication token from Discord."""

        self.ws = None
        """WebSocket connection."""

        self.interval = None
        """Heartbeat interval, in seconds."""

        self.get = get
        """Reading endpoint of the queue."""

        # Metadata
        self.user = None
        self.guilds = {}

    async def identify(self):
        """Send the identify message performing the authentication."""
        await self.ws.send_json({
            "op": IDENTIFY,
            "d": {
                "token": self.token,
                "properties": {},
                "compress": True,
                "large_threshold": 250
            }
        })

    async def heartbeat(self, fut):
        """Send beats regularly to keep the ws connected."""
        await asyncio.sleep(self.interval)
        while not fut.done():
            print("heartbeat", self.last_sequence)
            await self.ws.send_json({
                "op": HEARTBEAT,
                "d": self.last_sequence
            })
            await asyncio.sleep(self.interval)

    async def consume(self, fut):
        """Consume the queue and post messages in Discord."""
        while not fut.done():
            data = await self.get()
            msg = f"{data['repository']['name']}: {data['status_message']}!"
            # XXX this is quite hard coded.
            print(msg)
            asyncio.ensure_future(self.send_message(309734242085109760, msg))

    async def send_message(self, channel, content):
        """Send a message into the given channel."""
        return await api(f"/channels/{channel}/messages", "POST",
                         token=self.token,
                         json={"content": content})

    async def on_ready(self, data):
        """Handle the READY event."""
        self.user = data['user']
        print(f"connected as {self.user['username']}#{self.user['discriminator']}")

    async def on_guild_create(self, data):
        """Handle the GUILD_CREATE event."""
        self.guilds[data['id']] = data
        print(f"joined {data['name']}")

    async def on_presence_update(self, data):
        """Handle the PRESENCE_UPDATE event."""
        # XXX update the guilds.presences list.
        print(f"{data['user']['id']} is {data['status']}")

    async def run(self):
        """Run the bot."""
        running = asyncio.Future()  # XXX a bit ugly, still. Gather?

        with ClientSession() as session:
            url = f"{self.url}?v={API_VERSION}&encoding=json"
            async with session.ws_connect(url) as ws:
                self.ws = ws
                while not running.done():
                    # Reading the message, easier to handle timeouts and such.
                    msg = await ws.receive()
                    if msg.type == WSMsgType.TEXT:
                        data = json.loads(msg.data)
                    elif msg.type == WSMsgType.BINARY:
                        data = json.loads(zlib.decompress(msg.data))
                    elif msg.type == WSMsgType.CLOSE:
                        print("Close", msg.data, msg.extra)
                        running.cancel()
                        break
                    elif msg.type == WSMsgType.ERROR:
                        print("Error?")
                        running.cancel()
                        break
                    else:
                        print("unknown type", msg.type)

                    if data["op"] == HELLO:
                        await self.identify()

                        # Heartbeat (converted in seconds)
                        self.interval = data['d']['heartbeat_interval'] / 1000
                        asyncio.ensure_future(self.heartbeat(running))
                        # Consumer
                        asyncio.ensure_future(self.consume(running))

                    elif data["op"] == HEARTBEAT_ACK:
                        pass

                    elif data["op"] == DISPATCH:
                        self.last_sequence = data['s']

                        event = data['t'].lower()
                        if hasattr(self, f'on_{event}'):
                            method = getattr(self, f'on_{event}')
                            asyncio.ensure_future(method(data['d']))
                        else:
                            # Debug
                            print(data['t'])
                            print(data['d'])
                            print('-' * 40)

                    else:
                        print(data)

                # Close the heartbeat
                running.cancel()
