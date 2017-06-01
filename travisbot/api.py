"""Discord REST API tools."""

from aiohttp import ClientSession

from .conf import URL


async def api(path, method="GET", token=None, **kwargs):
    """Return the JSON body of a call to Discord REST API."""
    defaults = {
        "headers": {
            "User-Agent": "TravisBot (https://github.com/greut/travisbot)"
        }
    }

    if token:
        defaults["headers"]["Authorization"] = "Bot {0}".format(token)

    kwargs = dict(defaults, **kwargs)

    with ClientSession() as session:
        url = "{URL}{path}".format(URL=URL, path=path)
        async with session.request(method, url, **kwargs) as response:
            assert 200 == response.status, response.reason
            return await response.json()
