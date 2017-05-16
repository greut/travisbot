"""Main program."""

import asyncio
import os
import sys

from . import api, bot


async def main(token):
    """Run main program."""
    response = await api("/gateway")
    await bot(response['url'], token)


if __name__ == "__main__":
    token = os.environ.get('TOKEN')
    if not token:
        print("Please put the TOKEN in the env variables.", file=sys.stderr)
        sys.exit(1)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main(token))
    except KeyboardInterrupt:
        pass
    loop.close()
