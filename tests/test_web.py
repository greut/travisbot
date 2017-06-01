"""Testing the web module."""

import asyncio
import pytest

from aiohttp import web
from travisbot.web import make_app


@pytest.fixture
def app(loop):
    """Create the app for testing."""
    queue = asyncio.Queue(loop=loop)
    app = make_app(queue.put, loop)

    app['config']['queue'] = queue

    return app


async def test_fake(test_client, app):
    """Test the fake notifications."""
    client = await test_client(app)
    resp = await client.get('/notifications')

    assert resp.status == 200
    data = await resp.json()
    assert data['ok']

    status = await app['config']['queue'].get()
    assert 'status_message' in status
