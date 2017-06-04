"""Discord bot."""

import asyncio
import json
import zlib
from concurrent.futures import CancelledError
from urllib.parse import urlencode

from aiohttp import ClientSession, WSMsgType

from . import api


class Bot:
    """The bot."""

    API_VERSION = 6

    # OP_CODES
    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    STATUS_UPDATE = 3
    RESUME = 6
    INVALID_SESSION = 9
    HELLO = 10
    HEARTBEAT_ACK = 11

    def __init__(self, url, token, get, running):
        """Init the bot.

        :param url: The Gateway URL (WebSocket)
        :param token: The Discord API token
        :param get: The Queue reader side.
        """
        self.url = url
        self.running = running

        self.ws_running = None

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
        self.session_id = None
        self.user = None
        self.guilds = {}
        self.events = {}

        # all the tasks
        self.futures = []

    def event(self, prefix='on_'):
        """Decorate an function to register a dispatch event.

        :param prefix: the prefix str for the event. By default ``on_ready``.
        """
        def decorate(f):
            if f.__name__.startswith(prefix):
                self.events[f.__name__[len(prefix):]] = f
            return f
        return decorate

    async def _identify(self):
        """Send the identify/resume message performing the authentication."""
        if not self.session_id:
            msg = {
                "op": self.IDENTIFY,
                "d": {
                    "token": self.token,
                    "properties": {},
                    "compress": True,
                    "large_threshold": 250
                }
            }
        else:
            msg = {
                "op": self.RESUME,
                "d": {
                    "token": self.token,
                    "session_id": self.session_id,
                    "seq": self.last_sequence
                }
            }

        await self.ws.send_json(msg)

    async def _heartbeat(self):
        """Send beats regularly to keep the ws connected."""
        while not self.ws_running.done():
            # Wait for the future or send the heartbeat
            try:
                # Do not cancel the global future in case of a timeout
                # with shield.
                await asyncio.wait_for(asyncio.shield(self.ws_running),
                                       self.interval)
            except asyncio.TimeoutError:
                print("heartbeat", self.last_sequence)
                await self.ws.send_json({
                    "op": self.HEARTBEAT,
                    "d": self.last_sequence
                })

    # XXX move this outside the bot class.

    async def consume(self):
        """Consume the queue and post messages in Discord."""
        while not self.ws_running.done():
            task = asyncio.ensure_future(self.get())
            done, pending = await asyncio.wait(
                [task, self.ws_running],
                return_when=asyncio.FIRST_COMPLETED)

            if task in done:
                data = task.result()
                f = asyncio.ensure_future(self.send_message(self.channel_id, {
                    "embed": {
                        "title": ("{data[repository][owner_name]}/"
                                  "{data[repository][name]} "
                                  "{data[status_message]}"
                                  ).format(data=data),
                        "type": "rich",
                        "description": ("{data[author_name]} {data[type]} "
                                        "<{data[compare_url]}>"
                                        ).format(data=data),
                        "url": data['build_url']
                    }
                }))
                self.futures.append(f)
            else:
                task.cancel()
                break

    async def send_message(self, channel, data):
        """Send a message into the given channel."""
        return await api("/channels/{}/messages".format(channel), "POST",
                         token=self.token,
                         json=data)

    async def update_status(self, status):
        """Update the game status."""
        return await self.ws.send_json({
            "op": self.STATUS_UPDATE,
            "d": {
                "idle_since": None,
                "game": {
                    "name": status
                }
            }
        })

    async def _receive(self):
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
        with ClientSession() as session:
            url = self.url + "?"
            url += urlencode({"v": self.API_VERSION, "encoding": json})
            while not self.running.done():
                print("Bot is connecting...")
                self.ws_running = asyncio.Future()
                async with session.ws_connect(url) as ws:
                    self.ws = ws
                    while not self.running.done():
                        # Reading the message.
                        data = await self._receive()
                        if not data:
                            break

                        await self._handle(data)

                        # Cleanup
                        self.futures = [f
                                        for f in self.futures if not f.done()]

                    # Close the tasks
                    # Wait for them.
                    print("Bot is closing...")
                    self.ws_running.cancel()
                    while self.futures:
                        try:
                            await asyncio.gather(*self.futures)
                        except CancelledError:
                            pass
                        self.futures = [f
                                        for f in self.futures if not f.done()]

    async def _handle(self, data):
        """Handle the message data."""
        if data["op"] == self.HELLO:
            await self._identify()

            # Heartbeat (converted in seconds)
            self.interval = data['d']['heartbeat_interval'] / 1000
            self.futures.append(
                asyncio.ensure_future(self._heartbeat()))
            # Consumer
            self.futures.append(
                asyncio.ensure_future(self.consume()))

        elif data["op"] == self.HEARTBEAT_ACK:
            pass

        elif data["op"] == self.INVALID_SESSION:
            print('invalid session')

        elif data["op"] == self.DISPATCH:
            self.last_sequence = data['s']

            event = data['t'].lower()
            if event == 'ready':
                self.session_id = data['d']['session_id']
                self.futures.append(
                    asyncio.ensure_future(
                        self.update_status("greut/travisbot")))

            callback = self.events.get(event, None)
            if callback:
                self.futures.append(
                    asyncio.ensure_future(callback(data['d'])))
            else:
                # Debug
                print(data['t'])
                print(data['d'])
                print('-' * 40)

        else:
            print(data)
