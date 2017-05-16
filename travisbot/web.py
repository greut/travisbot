"""Web server handling the Travis webhooks."""

import json

from aiohttp import web


async def notifications(request):
    """Handle the Travis notifications."""
    # XXX verify the signature:
    # https://docs.travis-ci.com/user/notifications/

    # signature = request.headers.get['Signature']

    ok = False
    try:
        body = await request.post()
        data = json.loads(body['payload'])
        await request.app['config']['queue'].put(data)
        ok = True
    except KeyError:
        print("no payload?")
    except json.JSONDecodeError:
        print("no json?")
    return web.json_response({'ok': ok})


def make_app(token, queue):
    """Make the web application for you."""
    app = web.Application()
    app['config'] = {
        'token': token,
        'queue': queue
    }

    app.router.add_post('/notifications', notifications)

    return app
