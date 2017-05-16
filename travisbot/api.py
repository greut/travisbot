"""Discord REST API tools."""

from aiohttp import ClientSession

from .conf import URL


async def api(path):
    """Return the JSON body of a call to Discord REST API."""
    with ClientSession() as session:
        async with session.get(f"{URL}{path}") as response:
            assert 200 == response.status, response.reason
            return await response.json()
