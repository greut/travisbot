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
        # enqueue the payload
        await request.app['config']['put'](data)
        ok = True
    except KeyError:
        print("no payload?")
    except json.JSONDecodeError:
        print("no json?")
    return web.json_response({'ok': ok})


async def fake(request):
    """Submit a fake notification."""
    await request.app['config']['put']({
        'status_message': 'test',
        'repository': {
            'name': 'travisbot'
        }
    })
    return web.json_response({'ok': True})


def make_app(put):
    """Make the web application for you."""
    app = web.Application()
    app['config'] = {
        'put': put
    }

    app.router.add_get('/notifications', fake)
    app.router.add_post('/notifications', notifications)

    return app
