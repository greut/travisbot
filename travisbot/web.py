"""Web server handling the Travis webhooks."""

import base64
import json

from aiohttp import ClientSession, web
from OpenSSL import crypto

from . import TRAVIS_CONFIG_URL


async def notifications(request):
    """Handle the Travis notifications."""
    signature = request.headers.get('Signature', '')
    signature = base64.b64decode(signature)

    ok = False
    try:
        body = await request.post()
        payload = body['payload']
        certificate = request.app['config']['certificate']
        if not certificate:
            certificate = await travis_certificate()
            request.app['config']['certificate'] = certificate

        crypto.verify(certificate, signature, payload, 'sha1')
        data = json.loads(payload)
        # enqueue the payload
        await request.app['config']['put'](data)
        ok = True
    except crypto.Error:
        print("signature failure.")
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


async def travis_certificate():
    """Build the travis X509 certificate."""
    with ClientSession() as session:
        async with session.get(TRAVIS_CONFIG_URL) as response:
            assert 200 == response.status, response.reason
            body = await response.json()
            pkey = body['config']['notifications']['webhook']['public_key']

    certificate = crypto.X509()
    certificate.set_pubkey(crypto.load_publickey(crypto.FILETYPE_PEM, pkey))

    return certificate


def make_app(put):
    """Make the web application for you."""
    app = web.Application()
    app['config'] = {
        'put': put,
        'certificate': None
    }

    app.router.add_get('/notifications', fake)
    app.router.add_post('/notifications', notifications)

    return app
