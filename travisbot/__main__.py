"""Main program."""

import asyncio

import aiohttp


URL = "https://discordapp.com/api"
"""Discord HTTP API endpoint."""


async def api_call(path):
    """Return the JSON body of a call to Discord REST API."""
    with aiohttp.ClientSession() as session:
        async with session.get(f"{URL}{path}") as response:
            assert 200 == response.status, response.reason
            return await response.json()


async def main():
    """Run main program."""
    response = await api_call("/gateway")
    print(response)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
