"""Main program."""

import asyncio
import logging
import os
import sys
import warnings

from . import HOST, PORT, Bot, api, make_app


async def main(token, queue):
    """Run main program."""
    response = await api("/gateway")
    bot = Bot(response['url'], token, queue)

    @bot.event()
    async def on_ready(data):
        """Handle the READY event."""
        bot.user = data['user']
        print(("connected as {user[username]}"
               "#{user[discriminator]}").format(user=bot.user))

    @bot.event()
    async def on_guild_create(data):
        """Handle the GUILD_CREATE event."""
        bot.guilds[data['id']] = data
        print("joined {data[name]}".format(data=data))

    @bot.event()
    async def on_presence_update(data):
        """Handle the PRESENCE_UPDATE event."""
        # XXX update the guilds.presences list.
        print("{data[user][id]} is {data[status]}".format(data=data))

    # Other events:
    # on_typing_start
    # on_message_create
    # on_message_update
    # ...

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
        logging.getLogger('asyncio').addHandler(logging.StreamHandler())
        warnings.simplefilter('always', ResourceWarning)
    handler = app.make_handler(loop=loop)
    loop.run_until_complete(app.startup())

    server = loop.create_server(handler, host=HOST, port=PORT)
    try:
        srv = loop.run_until_complete(server)
        print("Listening on {HOST}:{PORT}... Ctrl-C to close."
              .format(HOST=HOST, PORT=PORT))
        loop.run_until_complete(main(token, queue.get))
    except KeyboardInterrupt:
        pass

    srv.close()
    loop.close()
