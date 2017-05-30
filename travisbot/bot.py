"""Discord bot."""

import asyncio
import json
import zlib

from aiohttp import ClientSession, WSMsgType

from . import api


class Bot:
    """The bot."""

    API_VERSION = 6

    # OP_CODES
    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    INVALID_SESSION = 9
    HELLO = 10
    HEARTBEAT_ACK = 11

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

        self.channel_id = 309734242085109760
        """Channel called #bots."""

        # Metadata
        self.user = None
        self.guilds = {}
        self.events = {}

    def event(self, prefix='on_'):
        """Decorator to register dispatch events.

        :param prefix: the prefix str for the event. By default ``on_ready``.
        """
        def decorate(f):
            if f.__name__.startswith(prefix):
                self.events[f.__name__[len(prefix):]] = f
            return f
        return decorate

    async def identify(self):
        """Send the identify message performing the authentication."""
        await self.ws.send_json({
            "op": self.IDENTIFY,
            "d": {
                "token": self.token,
                "properties": {},
                "compress": True,
                "large_threshold": 250
            }
        })

    async def heartbeat(self, fut):
        """Send beats regularly to keep the ws connected."""
        while True:
            task = asyncio.sleep(self.interval)
            done, pending = await asyncio.wait(
                [task, fut],
                return_when=asyncio.FIRST_COMPLETED)

            if task in done:
                print("heartbeat", self.last_sequence)
                await self.ws.send_json({
                    "op": self.HEARTBEAT,
                    "d": self.last_sequence
                })
            else:
                task.cancel()
                break

    async def consume(self, fut):
        """Consume the queue and post messages in Discord."""
        while True:
            task = self.get()
            done, pending = await asyncio.wait(
                [task, fut],
                return_when=asyncio.FIRST_COMPLETED)

            if task in done:
                data = task.get_result()
                asyncio.ensure_future(self.send_message(self.channel_id, {
                    "embed": {
                        "title": f"{data['repository']['owner_name']}/"
                                f"{data['repository']['name']} "
                                    f"{data['status_message']}",
                        "type": "rich",
                        "description": f"{data['author_name']} {data['type']} "
                                        f"<{data['compare_url']}>",
                        "url": data['build_url']
                    }
                }))
            else:
                task.cancel()
                break

    async def send_message(self, channel, data):
        """Send a message into the given channel."""
        return await api(f"/channels/{channel}/messages", "POST",
                         token=self.token,
                         json=data)

    async def receive(self):
        """Read the WebSocket and handles the various cases."""
        msg = await self.ws.receive()

        if msg.type == WSMsgType.TEXT:
            return json.loads(msg.data)

        elif msg.type == WSMsgType.BINARY:
            return json.loads(zlib.decompress(msg.data))

        elif msg.type == WSMsgType.CLOSE:
            print("Close", msg.data, msg.extra)

        elif msg.type == WSMsgType.ERROR:
            print("Error?", repr(msg.data))

        else:
            print("unknown type", msg.type)

    async def run(self):
        """Run the bot."""
        running = asyncio.Future()  # XXX a bit ugly, still. Gather?

        with ClientSession() as session:
            url = f"{self.url}?v={self.API_VERSION}&encoding=json"
            async with session.ws_connect(url) as ws:
                self.ws = ws
                futures = []
                while not running.done():
                    # Reading the message, easier to handle timeouts and such.
                    data = await self.receive()
                    if not data:
                        running.cancel()
                        break

                    if data["op"] == self.HELLO:
                        await self.identify()

                        # Heartbeat (converted in seconds)
                        self.interval = data['d']['heartbeat_interval'] / 1000
                        futures.append(asyncio.ensure_future(self.heartbeat(running)))
                        # Consumer
                        futures.append(asyncio.ensure_future(self.consume(running)))

                    elif data["op"] == self.HEARTBEAT_ACK:
                        pass

                    elif data["op"] == self.INVALID_SESSION:
                        print('invalid session')
                        running.cancel()

                    elif data["op"] == self.DISPATCH:
                        self.last_sequence = data['s']

                        event = data['t'].lower()
                        callback = self.events.get(event, None)
                        if callback:
                            futures.append(asyncio.ensure_future(callback(data['d'])))
                        else:
                            # Debug
                            print(data['t'])
                            print(data['d'])
                            print('-' * 40)

                    else:
                        print(data)

                    # Cleanup
                    futures = [f for f in futures if not f.done()]

                # Close the tasks
                running.cancel()
                # Wait for them.
                print("Bot is closing...")
                await asyncio.gather(*futures)
