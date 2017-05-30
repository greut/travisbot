"""Main program."""

import asyncio
import logging
import os
import sys

from . import HOST, PORT, Bot, api, make_app


async def main(token, queue):
    """Run main program."""
    response = await api("/gateway")
    bot = Bot(response['url'], token, queue)

    @bot.event()
    async def on_ready(data):
        """Handle the READY event."""
        bot.user = data['user']
        print(f"connected as {bot.user['username']}#{bot.user['discriminator']}")

    @bot.event()
    async def on_guild_create(data):
        """Handle the GUILD_CREATE event."""
        bot.guilds[data['id']] = data
        print(f"joined {data['name']}")

    @bot.event()
    async def on_presence_update(data):
        """Handle the PRESENCE_UPDATE event."""
        # XXX update the guilds.presences list.
        print(f"{data['user']['id']} is {data['status']}")


    await bot.run()


if __name__ == "__main__":
    token = os.environ.get('TOKEN')
    if not token:
        print("Please put the TOKEN in the env variables.", file=sys.stderr)
        sys.exit(1)

    debug = True

    queue = asyncio.Queue()

    app = make_app(queue.put)

    loop = asyncio.get_event_loop()
    if debug:
        loop.set_debug(True)
        logging.getLogger('asyncio').setLevel(logging.DEBUG)
    handler = app.make_handler(loop=loop)
    loop.run_until_complete(app.startup())

    server = loop.create_server(handler, host=HOST, port=PORT)
    try:
        srv = loop.run_until_complete(server)
        print(f"Listening on {HOST}:{PORT}... Ctrl-C to close.")
        loop.run_until_complete(main(token, queue.get))
    except KeyboardInterrupt:
        pass

    srv.close()
    loop.close()
